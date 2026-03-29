"""
Continuous Orchestration Pipeline for Comrade ML Models.

ONE-SITE-AT-A-TIME scraping to avoid IP blacklisting.
Splits scraped data into 3 model-specific directories.
Trains all 3 models SEQUENTIALLY after enough data is collected.
Reports live progress to scrape_status.json for the React dashboard.

Usage:
  python -m ML.training.continuous_pipeline              # Full cycle (all sites)
  python -m ML.training.continuous_pipeline --site JumiaKEScraper  # Single site
  python -m ML.training.continuous_pipeline --scrape-only           # Scrape without training
"""

import os
import sys
import time
import json
import glob
import argparse
import pandas as pd
import numpy as np
from datetime import datetime
import logging

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'pipeline.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ContinuousPipeline")

# Configuration
MIN_ROWS_PER_MODEL = 100
SITE_COOLDOWN_SECONDS = 60     # Delay between scraping different sites
MAX_CATEGORIES_PER_SITE = 20   # Limit categories per site to stay polite
ITEMS_PER_CATEGORY = 100       # Items per category

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(PIPELINE_DIR), 'data')

PRICING_DATA_DIR = os.path.join(DATA_DIR, 'pricing_data')
REC_DATA_DIR = os.path.join(DATA_DIR, 'recommendation_data')
DIST_DATA_DIR = os.path.join(DATA_DIR, 'distribution_data')
RAW_DATA_DIR = os.path.join(DATA_DIR, 'raw_scraped')
STATUS_FILE = os.path.join(DATA_DIR, 'scrape_status.json')

TRAIN_PRICING = os.path.join(PIPELINE_DIR, 'train_pricing.py')
TRAIN_REC = os.path.join(PIPELINE_DIR, 'recommendation_pipeline.py')
TRAIN_DIST = os.path.join(PIPELINE_DIR, 'distribution_model.py')

for d in [PRICING_DATA_DIR, REC_DATA_DIR, DIST_DATA_DIR, RAW_DATA_DIR]:
    os.makedirs(d, exist_ok=True)


# ── Import all scrapers to populate the registry ─────────────────────────────
def _load_all_scrapers():
    """Import every regional scraper module so @register_scraper fires."""
    from ML.training.data_scrapers.base_scraper import SCRAPER_REGISTRY
    scraper_modules = [
        'ML.training.data_scrapers.kenya_scrapers',
        'ML.training.data_scrapers.africa_scrapers',
        'ML.training.data_scrapers.na_scrapers',
        'ML.training.data_scrapers.sa_scrapers',
        'ML.training.data_scrapers.europe_scrapers',
        'ML.training.data_scrapers.asia_scrapers',
        'ML.training.data_scrapers.oceania_scrapers',
    ]
    import importlib
    for mod_name in scraper_modules:
        try:
            importlib.import_module(mod_name)
        except Exception as e:
            logger.warning(f"Could not import {mod_name}: {e}")
    return SCRAPER_REGISTRY


# ── Status Reporter ──────────────────────────────────────────────────────────

def update_status(status_msg, phase="idle", current_site="", size=0.0,
                  pricing=None, recommendation=None, distribution=None,
                  goal_matching=None, goal_drift=None):
    """Write the current pipeline state to scrape_status.json for the frontend."""
    try:
        data = {
            "status": status_msg,
            "phase": phase,
            "current_site": current_site,
            "current_size_gb": round(size, 4),
            "target_rows": MIN_ROWS_PER_MODEL,
            "pricing": pricing or {"status": "idle", "rows": 0, "progress_pct": 0},
            "recommendation": recommendation or {"status": "idle", "rows": 0, "progress_pct": 0},
            "distribution": distribution or {"status": "idle", "rows": 0, "progress_pct": 0},
            "goal_matching": goal_matching or {"status": "idle", "rows": 0, "progress_pct": 0},
            "goal_drift": goal_drift or {"status": "idle", "rows": 0, "progress_pct": 0},
            "timestamp": datetime.now().isoformat()
        }
        with open(STATUS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing status: {e}")


# ── Directory metrics ────────────────────────────────────────────────────────

def get_dir_size_gb(directory):
    total_size = 0
    for dirpath, _, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size / (1024 * 1024 * 1024)


def count_rows_in_dir(directory):
    total = 0
    for f in glob.glob(os.path.join(directory, '*.parquet')):
        try:
            df = pd.read_parquet(f)
            total += len(df)
        except Exception:
            pass
    return total


# ── ONE-SITE-AT-A-TIME Scraper ───────────────────────────────────────────────

def scrape_single_site(scraper_name, scraper_class):
    """
    Scrape a single site, save raw data, return row count.
    This is the core anti-blacklisting mechanism: only one site runs at a time.
    """
    logger.info(f"{'='*50}")
    logger.info(f"  SCRAPING: {scraper_name}")
    logger.info(f"{'='*50}")
    
    update_status(
        f"Scraping {scraper_name}", "scraping",
        current_site=scraper_name,
        size=get_dir_size_gb(RAW_DATA_DIR)
    )
    
    try:
        scraper = scraper_class()
        rows = scraper.run_scraper(
            max_categories=MAX_CATEGORIES_PER_SITE,
            items_per_category=ITEMS_PER_CATEGORY,
            output_dir=RAW_DATA_DIR
        )
        logger.info(f"  {scraper_name}: extracted {rows} rows")
        return rows
    except Exception as e:
        logger.error(f"  {scraper_name} failed: {e}")
        return 0


def scrape_all_sites_sequentially(registry, only_site=None):
    """
    Scrape sites ONE AT A TIME with cooldown between each.
    If only_site is specified, scrape just that one site.
    """
    total_rows = 0
    sites = list(registry.items())
    
    if only_site:
        sites = [(k, v) for k, v in sites if k == only_site]
        if not sites:
            logger.error(f"Site '{only_site}' not found in registry. Available: {list(registry.keys())}")
            return 0
    
    for idx, (name, cls) in enumerate(sites):
        rows = scrape_single_site(name, cls)
        total_rows += rows
        
        # Cooldown between sites (skip after last site)
        if idx < len(sites) - 1:
            logger.info(f"  Cooling down {SITE_COOLDOWN_SECONDS}s before next site...")
            update_status(
                f"Cooldown after {name}", "cooldown",
                current_site=f"waiting ({SITE_COOLDOWN_SECONDS}s)",
                size=get_dir_size_gb(RAW_DATA_DIR)
            )
            time.sleep(SITE_COOLDOWN_SECONDS)
    
    logger.info(f"All sites scraped. Total rows: {total_rows}")
    return total_rows


# ── Data Splitter ────────────────────────────────────────────────────────────

def split_scraped_data():
    """Split raw parquet files into 3 model-specific directories."""
    logger.info("Splitting raw scraped data into 3 model-specific directories...")
    
    raw_files = glob.glob(os.path.join(RAW_DATA_DIR, '*.parquet'))
    if not raw_files:
        logger.info("No raw data files found to split.")
        return
    
    pricing_rows, rec_rows, dist_rows = [], [], []
    
    for f in raw_files:
        try:
            df = pd.read_parquet(f)
            if 'category' not in df.columns:
                df['category'] = 'General'
            if 'is_digital' not in df.columns:
                df['is_digital'] = False
            
            pricing_cols = ['product_name', 'category', 'platform', 'country',
                           'price_kes', 'original_price_kes', 'discount_pct',
                           'rating', 'reviews_count', 'demand_signal', 'is_digital', 'timestamp']
            pricing_rows.append(df[[c for c in pricing_cols if c in df.columns]])
            
            rec_cols = ['product_name', 'category', 'platform', 'country', 'price_kes', 'timestamp']
            rec_rows.append(df[[c for c in rec_cols if c in df.columns]])
            
            dist_cols = ['product_name', 'category', 'platform', 'country',
                        'price_kes', 'original_price_kes', 'discount_pct', 'is_digital', 'timestamp']
            dist_rows.append(df[[c for c in dist_cols if c in df.columns]])
        except Exception as e:
            logger.error(f"Error reading {f}: {e}")
    
    ts = int(time.time())
    if pricing_rows:
        pd.concat(pricing_rows, ignore_index=True).to_parquet(
            os.path.join(PRICING_DATA_DIR, f'pricing_{ts}.parquet'))
    if rec_rows:
        pd.concat(rec_rows, ignore_index=True).to_parquet(
            os.path.join(REC_DATA_DIR, f'recommendation_{ts}.parquet'))
    if dist_rows:
        pd.concat(dist_rows, ignore_index=True).to_parquet(
            os.path.join(DIST_DATA_DIR, f'distribution_{ts}.parquet'))


# ── Sequential Model Training ────────────────────────────────────────────────

def run_training(model_name, cmd, model_key, rows_count):
    """Run a single model training as a subprocess."""
    import subprocess
    
    logger.info(f"{'='*60}")
    logger.info(f"  TRAINING: {model_name} ({rows_count} rows)")
    logger.info(f"{'='*60}")
    
    update_status(f"Training {model_name}", "training", current_site="")
    
    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )
        for line in process.stdout:
            clean = line.strip()
            if clean:
                logger.info(f"[{model_key.upper()}] {clean}")
        process.wait()
        
        if process.returncode == 0:
            logger.info(f"{model_name} training completed successfully.")
            return True
        else:
            logger.error(f"{model_name} training failed (exit {process.returncode})")
            return False
    except Exception as e:
        logger.error(f"Failed to execute {model_name} training: {e}")
        return False


def train_all_models_sequentially():
    """Train all 3 models sequentially."""
    p_rows = count_rows_in_dir(PRICING_DATA_DIR)
    r_rows = count_rows_in_dir(REC_DATA_DIR)
    d_rows = count_rows_in_dir(DIST_DATA_DIR)
    
    logger.info(f"Data ready — Pricing: {p_rows} | Rec: {r_rows} | Dist: {d_rows}")
    
    if p_rows >= MIN_ROWS_PER_MODEL:
        run_training("Pricing RL Agent", [
            sys.executable, TRAIN_PRICING,
            "--episodes", "100", "--eval-interval", "25",
            "--resume", "--data-file", PRICING_DATA_DIR
        ], "pricing", p_rows)
    
    if r_rows >= MIN_ROWS_PER_MODEL:
        run_training("Recommendation NN", [
            sys.executable, TRAIN_REC,
            "--epochs", "50", "--data-dir", REC_DATA_DIR
        ], "recommendation", r_rows)
    
    if d_rows >= MIN_ROWS_PER_MODEL:
        run_training("Distribution Model", [
            sys.executable, TRAIN_DIST,
            "--epochs", "200", "--data-dir", DIST_DATA_DIR
        ], "distribution", d_rows)
    
    update_status("All Training Complete", "idle",
        pricing={"status": "complete", "rows": p_rows, "progress_pct": 100},
        recommendation={"status": "complete", "rows": r_rows, "progress_pct": 100},
        distribution={"status": "complete", "rows": d_rows, "progress_pct": 100},
    )


# ── Main Orchestrator ────────────────────────────────────────────────────────

def run_pipeline(only_site=None, scrape_only=False):
    """Main continuous orchestration loop."""
    registry = _load_all_scrapers()
    
    logger.info("=" * 60)
    logger.info("  Comrade ML Pipeline — ONE-SITE-AT-A-TIME mode")
    logger.info(f"  Available scrapers: {list(registry.keys())}")
    logger.info(f"  Cooldown between sites: {SITE_COOLDOWN_SECONDS}s")
    logger.info("=" * 60)
    
    cycle = 1
    while True:
        logger.info(f"--- Cycle {cycle} ---")
        
        # 1. Scrape sites sequentially
        scrape_all_sites_sequentially(registry, only_site=only_site)
        
        # 2. Split into model directories
        split_scraped_data()
        
        if scrape_only:
            logger.info("--scrape-only mode: skipping training.")
        else:
            # 3. Train all models
            train_all_models_sequentially()
        
        # 4. Clean raw data
        for f in glob.glob(os.path.join(RAW_DATA_DIR, '*')):
            try:
                os.remove(f)
            except Exception:
                pass
        
        if only_site:
            logger.info("Single-site mode: exiting after one cycle.")
            break
        
        cycle += 1
        logger.info("Cooling down 2 minutes before next cycle...")
        update_status("Cooldown Between Cycles", "cooldown")
        time.sleep(120)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Comrade ML Continuous Pipeline")
    parser.add_argument('--site', type=str, default=None,
                        help='Scrape only this site (e.g. JumiaKEScraper)')
    parser.add_argument('--scrape-only', action='store_true',
                        help='Only scrape data, skip training')
    args = parser.parse_args()
    run_pipeline(only_site=args.site, scrape_only=args.scrape_only)
