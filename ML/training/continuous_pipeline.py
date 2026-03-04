"""
Continuous Orchestration Pipeline for Comrade ML Models.

Manages data scraping across 28 global platforms.
Splits scraped data into 3 model-specific directories.
Trains all 3 models SEQUENTIALLY after enough data is collected.
Reports live progress to scrape_status.json for the React dashboard.
"""

import os
import sys
import time
import json
import glob
import pandas as pd
import numpy as np
import subprocess
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
MIN_ROWS_PER_MODEL = 100      # Minimum rows before training fires
MIN_CATEGORIES = 100           # Minimum unique categories target

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(PIPELINE_DIR), 'data')

# Three separate data directories for the three models
PRICING_DATA_DIR = os.path.join(DATA_DIR, 'pricing_data')
REC_DATA_DIR = os.path.join(DATA_DIR, 'recommendation_data')
DIST_DATA_DIR = os.path.join(DATA_DIR, 'distribution_data')
RAW_DATA_DIR = os.path.join(DATA_DIR, 'raw_scrapped')
STATUS_FILE = os.path.join(DATA_DIR, 'scrape_status.json')

# Training scripts
TRAIN_PRICING = os.path.join(PIPELINE_DIR, 'train_pricing.py')
TRAIN_REC = os.path.join(PIPELINE_DIR, 'recommendation_pipeline.py')
TRAIN_DIST = os.path.join(PIPELINE_DIR, 'distribution_model.py')

for d in [PRICING_DATA_DIR, REC_DATA_DIR, DIST_DATA_DIR, RAW_DATA_DIR]:
    os.makedirs(d, exist_ok=True)

# ---------------------------------------------------------------------------
#  Status Reporter — writes JSON that Django serves to the React dashboard
# ---------------------------------------------------------------------------

def update_status(status_msg, phase="idle", active=0, size=0.0, 
                  pricing=None, recommendation=None, distribution=None):
    """Write the current pipeline state to scrape_status.json for the frontend."""
    try:
        data = {
            "status": status_msg,
            "phase": phase,
            "active_scrapers": active,
            "current_size_gb": round(size, 4),
            "target_rows": MIN_ROWS_PER_MODEL,
            "pricing": pricing or {"status": "idle", "rows": 0, "progress_pct": 0},
            "recommendation": recommendation or {"status": "idle", "rows": 0, "progress_pct": 0},
            "distribution": distribution or {"status": "idle", "rows": 0, "progress_pct": 0},
            "timestamp": datetime.now().isoformat()
        }
        with open(STATUS_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Error writing status: {e}")


# ---------------------------------------------------------------------------
#  Directory metrics
# ---------------------------------------------------------------------------

def get_dir_size_gb(directory):
    """Calculate the total size of a directory in GB."""
    total_size = 0
    for dirpath, _, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size / (1024 * 1024 * 1024)


def count_rows_in_dir(directory):
    """Count total rows across all parquet files in a directory."""
    total = 0
    for f in glob.glob(os.path.join(directory, '*.parquet')):
        try:
            df = pd.read_parquet(f)
            total += len(df)
        except:
            pass
    return total


def count_categories_in_dir(directory):
    """Count unique categories across all parquet files in a directory."""
    cats = set()
    for f in glob.glob(os.path.join(directory, '*.parquet')):
        try:
            df = pd.read_parquet(f)
            if 'category' in df.columns:
                cats.update(df['category'].dropna().unique())
        except:
            pass
    return len(cats)


# ---------------------------------------------------------------------------
#  Scraper Launcher
# ---------------------------------------------------------------------------

def trigger_scrapers():
    """Launch all 7 regional scraper processes."""
    logger.info("Triggering data scrapers across 7 continents...")
    
    active_processes = []
    scrapers_dir = os.path.join(PIPELINE_DIR, 'data_scrapers')
    
    scripts = [
        'kenya_scrapers', 'africa_scrapers', 'na_scrapers',
        'sa_scrapers', 'europe_scrapers', 'asia_scrapers', 'oceania_scrapers'
    ]
    
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    for script in scripts:
        script_path = os.path.join(scrapers_dir, f"{script}.py")
        if os.path.exists(script_path):
            cmd = [sys.executable, '-m', f"ML.training.data_scrapers.{script}"]
            proc = subprocess.Popen(cmd, cwd=project_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            active_processes.append(proc)
        else:
            logger.warning(f"Script missing: {script_path}")
            
    update_status("Scraping Data", "scraping", len(active_processes), get_dir_size_gb(RAW_DATA_DIR))
    return active_processes


# ---------------------------------------------------------------------------
#  Scraping Monitor — checks rows collected and splits data
# ---------------------------------------------------------------------------

def split_scraped_data():
    """
    Read all raw parquet files and split the rows into the 3 model-specific folders.
    
    - pricing_data/: price, discount, ratings, demand signals
    - recommendation_data/: product_name, category (for text classification)
    - distribution_data/: price, category, is_digital (for tier distribution)
    """
    logger.info("Splitting raw scraped data into 3 model-specific directories...")
    
    raw_files = glob.glob(os.path.join(RAW_DATA_DIR, '*.parquet'))
    if not raw_files:
        logger.info("No raw data files found to split.")
        return
    
    pricing_rows = []
    rec_rows = []
    dist_rows = []
    
    for f in raw_files:
        try:
            df = pd.read_parquet(f)
            
            # Ensure required columns exist with defaults
            if 'category' not in df.columns:
                df['category'] = 'General'
            if 'is_digital' not in df.columns:
                df['is_digital'] = False
            
            # --- Pricing Data: needs price, discount, demand, ratings ---
            pricing_cols = ['product_name', 'category', 'platform', 'country',
                           'price_kes', 'original_price_kes', 'discount_pct',
                           'rating', 'reviews_count', 'demand_signal', 'is_digital', 'timestamp']
            available = [c for c in pricing_cols if c in df.columns]
            pricing_rows.append(df[available])
            
            # --- Recommendation Data: needs text + category labels ---
            rec_cols = ['product_name', 'category', 'platform', 'country', 'price_kes', 'timestamp']
            available = [c for c in rec_cols if c in df.columns]
            rec_rows.append(df[available])
            
            # --- Distribution Data: needs price, tier info, buy mode ---
            dist_cols = ['product_name', 'category', 'platform', 'country',
                        'price_kes', 'original_price_kes', 'discount_pct', 'is_digital', 'timestamp']
            available = [c for c in dist_cols if c in df.columns]
            dist_rows.append(df[available])
            
        except Exception as e:
            logger.error(f"Error reading {f}: {e}")
    
    # Save concatenated data
    ts = int(time.time())
    
    if pricing_rows:
        pricing_df = pd.concat(pricing_rows, ignore_index=True)
        pricing_df.to_parquet(os.path.join(PRICING_DATA_DIR, f'pricing_{ts}.parquet'))
        logger.info(f"Pricing data: {len(pricing_df)} rows saved")
        
    if rec_rows:
        rec_df = pd.concat(rec_rows, ignore_index=True)
        rec_df.to_parquet(os.path.join(REC_DATA_DIR, f'recommendation_{ts}.parquet'))
        logger.info(f"Recommendation data: {len(rec_df)} rows saved")
        
    if dist_rows:
        dist_df = pd.concat(dist_rows, ignore_index=True)
        dist_df.to_parquet(os.path.join(DIST_DATA_DIR, f'distribution_{ts}.parquet'))
        logger.info(f"Distribution data: {len(dist_df)} rows saved")


def monitor_scraping(active_processes):
    """Monitor raw data directory. Returns True if enough data collected or all scrapers done."""
    current_size = get_dir_size_gb(RAW_DATA_DIR)
    raw_rows = count_rows_in_dir(RAW_DATA_DIR)
    raw_cats = count_categories_in_dir(RAW_DATA_DIR)
    
    alive = [p for p in active_processes if p.poll() is None]
    update_status(
        f"Scraping: {raw_rows} rows, {raw_cats} categories",
        "scraping", len(alive), current_size,
        pricing={"status": "queued", "rows": raw_rows, "progress_pct": 0},
        recommendation={"status": "queued", "rows": raw_rows, "progress_pct": 0},
        distribution={"status": "queued", "rows": raw_rows, "progress_pct": 0},
    )
    
    logger.info(f"Scraping: {raw_rows} rows | {raw_cats} categories | {len(alive)} alive | {current_size:.3f} GB")
    
    if len(alive) < len(active_processes):
        logger.warning(f"{len(active_processes) - len(alive)} scraper processes completed or died.")
    
    # Stop when we have enough data OR all scrapers are done
    if raw_rows >= MIN_ROWS_PER_MODEL or len(alive) == 0:
        logger.info(f"Stopping scrapers. Collected {raw_rows} rows across {raw_cats} categories.")
        for p in alive:
            try:
                p.terminate()
            except:
                pass
        return True
    return False


# ---------------------------------------------------------------------------
#  Sequential Model Training
# ---------------------------------------------------------------------------

def run_training(model_name, cmd, model_status_key, rows_count):
    """Run a single model training as a subprocess, streaming logs to pipeline.log."""
    logger.info(f"{'='*60}")
    logger.info(f"  TRAINING: {model_name}")
    logger.info(f"  Rows: {rows_count}")
    logger.info(f"{'='*60}")
    
    # Update status: mark this model as training
    status_update = {
        "pricing": {"status": "complete" if model_status_key != "pricing" else "training", "rows": rows_count, "progress_pct": 0},
        "recommendation": {"status": "complete" if model_status_key == "distribution" else ("training" if model_status_key == "recommendation" else "queued"), "rows": rows_count, "progress_pct": 0},
        "distribution": {"status": "training" if model_status_key == "distribution" else "queued", "rows": rows_count, "progress_pct": 0},
    }
    update_status(f"Training {model_name}", "training", 0, 0, **status_update)
    
    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )
        
        for line in process.stdout:
            clean_line = line.strip()
            if clean_line:
                logger.info(f"[{model_status_key.upper()}] {clean_line}")
        
        process.wait()
        
        if process.returncode == 0:
            logger.info(f"{model_name} training completed successfully.")
            return True
        else:
            logger.error(f"{model_name} training failed with exit code {process.returncode}")
            return False
    except Exception as e:
        logger.error(f"Failed to execute {model_name} training: {e}")
        return False


def train_all_models_sequentially():
    """Train all 3 models sequentially to avoid overwhelming the PC."""
    
    pricing_rows = count_rows_in_dir(PRICING_DATA_DIR)
    rec_rows = count_rows_in_dir(REC_DATA_DIR)
    dist_rows = count_rows_in_dir(DIST_DATA_DIR)
    
    logger.info(f"Data ready — Pricing: {pricing_rows} | Rec: {rec_rows} | Dist: {dist_rows}")
    
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # --- Step 1: Pricing RL Agent ---
    if pricing_rows >= MIN_ROWS_PER_MODEL:
        cmd = [
            sys.executable, TRAIN_PRICING,
            "--episodes", "100",
            "--eval-interval", "25",
            "--resume",
            "--data-file", PRICING_DATA_DIR
        ]
        run_training("Pricing RL Agent", cmd, "pricing", pricing_rows)
    else:
        logger.warning(f"Pricing: only {pricing_rows} rows, need {MIN_ROWS_PER_MODEL}. Skipping.")
    
    # --- Step 2: Recommendation NN ---
    if rec_rows >= MIN_ROWS_PER_MODEL:
        cmd = [
            sys.executable, TRAIN_REC,
            "--epochs", "50",
            "--data-dir", REC_DATA_DIR
        ]
        run_training("Recommendation NN", cmd, "recommendation", rec_rows)
    else:
        logger.warning(f"Recommendation: only {rec_rows} rows, need {MIN_ROWS_PER_MODEL}. Skipping.")
    
    # --- Step 3: Distribution Model ---
    if dist_rows >= MIN_ROWS_PER_MODEL:
        cmd = [
            sys.executable, TRAIN_DIST,
            "--epochs", "200",
            "--data-dir", DIST_DATA_DIR
        ]
        run_training("Distribution Model", cmd, "distribution", dist_rows)
    else:
        logger.warning(f"Distribution: only {dist_rows} rows, need {MIN_ROWS_PER_MODEL}. Skipping.")
    
    # All done
    update_status(
        "All Training Complete", "idle", 0, 0,
        pricing={"status": "complete", "rows": pricing_rows, "progress_pct": 100},
        recommendation={"status": "complete", "rows": rec_rows, "progress_pct": 100},
        distribution={"status": "complete", "rows": dist_rows, "progress_pct": 100},
    )


# ---------------------------------------------------------------------------
#  Main Orchestrator
# ---------------------------------------------------------------------------

def run_pipeline():
    """Main continuous orchestration loop."""
    logger.info("=" * 60)
    logger.info("  Starting Comrade ML Data Scraping & Training Pipeline")
    logger.info(f"  Target: {MIN_ROWS_PER_MODEL}+ rows | {MIN_CATEGORIES}+ categories")
    logger.info("=" * 60)
    
    cycle_count = 1
    
    while True:
        logger.info(f"--- Starting Pipeline Cycle {cycle_count} ---")
        
        # 1. Start scraping
        active_processes = trigger_scrapers()
        
        # 2. Monitor until enough data
        while not monitor_scraping(active_processes):
            time.sleep(30)
        
        # 3. Split raw data into 3 model directories
        split_scraped_data()
        
        # 4. Report data counts
        p_rows = count_rows_in_dir(PRICING_DATA_DIR)
        r_rows = count_rows_in_dir(REC_DATA_DIR)
        d_rows = count_rows_in_dir(DIST_DATA_DIR)
        logger.info(f"Data split complete — Pricing: {p_rows} | Rec: {r_rows} | Dist: {d_rows}")
        
        # 5. Train all 3 models sequentially
        train_all_models_sequentially()
        
        # 6. Clean up raw data (keep model-specific data for re-training)
        logger.info("Cleaning up raw scraped data...")
        for f in glob.glob(os.path.join(RAW_DATA_DIR, '*')):
            try:
                os.remove(f)
            except:
                pass
        
        cycle_count += 1
        logger.info("Cooling down for 2 minutes before next cycle...")
        update_status("Cooling Down", "cooldown", 0, 0.0)
        time.sleep(120)


if __name__ == '__main__':
    run_pipeline()
