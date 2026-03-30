"""
Base Secure Scraper for the Comrade Pricing Data Pipeline.

Handles:
- User-Agent rotation
- Request delays (exponential backoff)
- BeautifulSoup parsing
- Robust error handling to avoid bot detection
- Category extraction from URL slugs
- Separate output directories per model
- Scraper registry for sequential orchestration
"""

import os
import re
import time
import random
import logging
import requests
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod


# ── Global Scraper Registry ──────────────────────────────────────────────────
# Every BaseScraper subclass that calls @register_scraper is added here.
# continuous_pipeline.py reads this to know which scrapers are available.
SCRAPER_REGISTRY: dict = {}   # { "JumiaKE": <class JumiaKEScraper>, ... }


def register_scraper(cls):
    """Class decorator: register a BaseScraper subclass into SCRAPER_REGISTRY."""
    SCRAPER_REGISTRY[cls.__name__] = cls
    return cls


# Common user agents to avoid detection
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
]

# Known digital product categories (for pricing rules)
DIGITAL_CATEGORIES = {
    'software', 'apps', 'ebooks', 'e-books', 'digital', 'subscriptions',
    'streaming', 'games', 'digital-games', 'music', 'movies', 'courses',
    'online-services', 'saas', 'licenses', 'downloads', 'gift-cards',
}


# ── Robots.txt cache ─────────────────────────────────────────────────────────
_robots_cache: dict = {}


def check_robots_txt(url: str, user_agent: str = '*') -> bool:
    """Return True if robots.txt allows scraping this URL."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    if robots_url not in _robots_cache:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
        except Exception:
            return True  # If we can't read robots.txt, proceed cautiously
        _robots_cache[robots_url] = rp
    return _robots_cache[robots_url].can_fetch(user_agent, url)



def extract_category_from_url(url):
    """Extract a human-readable category name from a URL path slug."""
    from urllib.parse import urlparse
    path = urlparse(url).path.strip('/')
    # Take the last meaningful segment
    parts = [p for p in path.split('/') if p and not p.isdigit() and len(p) > 1]
    if not parts:
        return "General"
    slug = parts[-1]
    # Clean up: replace hyphens/underscores, title case
    name = re.sub(r'[-_]+', ' ', slug).strip().title()
    return name if name else "General"


def is_digital_category(category_name):
    """Check if a category is digital (software, ebooks, etc.)."""
    lower = category_name.lower().replace(' ', '-')
    return any(d in lower for d in DIGITAL_CATEGORIES)


class BaseScraper(ABC):
    """
    Abstract base class for all regional platform scrapers.
    """
    
    def __init__(self, platform_name, base_url, delay_range=(2.0, 5.0)):
        self.platform_name = platform_name
        self.base_url = base_url
        self.delay_range = delay_range
        self.session = requests.Session()
        
        # Configure logging
        self.logger = logging.getLogger(f"scraper.{platform_name}")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _get_headers(self):
        """Generate random headers for each request."""
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
    
    def _delay(self):
        """Sleep for a random time to mimic human behavior."""
        sleep_time = random.uniform(*self.delay_range)
        time.sleep(sleep_time)
    
    def fetch_page(self, url, params=None, max_retries=3):
        """
        Securely fetch a page with exponential backoff.
        """
        for attempt in range(max_retries):
            self._delay()
            try:
                response = self.session.get(
                    url, 
                    headers=self._get_headers(), 
                    params=params, 
                    timeout=15
                )
                
                if response.status_code == 200:
                    return BeautifulSoup(response.content, 'html.parser')
                elif response.status_code in [403, 429]:
                    # Rate limited or blocked
                    wait_time = (2 ** attempt) * 5 + random.uniform(1, 5)
                    self.logger.warning(f"Blocked (HTTP {response.status_code}). Waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"HTTP {response.status_code} on {url}")
                    return None
                    
            except requests.RequestException as e:
                wait_time = (2 ** attempt) * 2
                self.logger.warning(f"Request failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                
        self.logger.error(f"Failed to fetch {url} after {max_retries} attempts.")
        return None

    def fetch_api(self, url, params=None, max_retries=3):
        """
        Securely fetch from a platform's public JSON API if available.
        """
        for attempt in range(max_retries):
            self._delay()
            headers = self._get_headers()
            headers['Accept'] = 'application/json'
            
            try:
                response = self.session.get(url, headers=headers, params=params, timeout=15)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in [403, 429]:
                    wait_time = (2 ** attempt) * 5
                    time.sleep(wait_time)
                else:
                    return None
            except requests.RequestException:
                time.sleep((2 ** attempt) * 2)
        return None

    @abstractmethod
    def discover_categories(self, max_categories=500):
        """
        Dynamically discover category URLs from the platform's homepage or sitemap.
        Should return a list of up to `max_categories` URLs.
        """
        pass

    @abstractmethod
    def scrape_category(self, category_url, max_items=1000):
        """
        Scrape items from a specific category URL.
        Must yield dictionaries with keys:
        [product_name, category, price_kes, original_price_kes, discount_pct, 
         rating, reviews_count, demand_signal, platform, country, is_digital, timestamp]
        """
        pass
    
    def run_scraper(self, max_categories=500, items_per_category=200, output_dir=None):
        """
        Main entry point for the specific platform scraper.
        Extracts up to (max_categories * items_per_category) items.
        Handles batch saving to disk directly.
        """
        import pandas as pd
        import datetime
        
        # Use provided output_dir or fall back to default raw_scrapped
        if output_dir is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(os.path.dirname(base), 'data', 'raw_scrapped')
        
        os.makedirs(output_dir, exist_ok=True)
        
        self.logger.info(f"Starting {self.platform_name} scraper...")
        categories = self.discover_categories(max_categories=max_categories)
        self.logger.info(f"Discovered {len(categories)} categories")
        
        results = []
        total_extracted = 0
        batch_count = 1
        
        for idx, cat_url in enumerate(categories):
            # Extract category name from the URL
            cat_name = extract_category_from_url(cat_url)
            digital = is_digital_category(cat_name)
            
            self.logger.info(f"Scraping category {idx+1}/{len(categories)}: {cat_name} ({cat_url})")
            for item in self.scrape_category(cat_url, max_items=items_per_category):
                # Enrich item with category metadata
                item['category'] = item.get('category', cat_name)
                item['is_digital'] = item.get('is_digital', digital)
                results.append(item)
                total_extracted += 1
                
                # Save in batches of 50 for faster visual feedback
                if len(results) >= 50:
                    df = pd.DataFrame(results)
                    file_path = os.path.join(output_dir, f"{self.platform_name}_batch_{batch_count}_{int(time.time())}.parquet")
                    df.to_parquet(file_path)
                    self.logger.info(f"Saved batch {batch_count} ({len(df)} rows) -> {file_path}")
                    results = []
                    batch_count += 1
                    
        # Save remaining items
        if results:
            df = pd.DataFrame(results)
            file_path = os.path.join(output_dir, f"{self.platform_name}_batch_{batch_count}_{int(time.time())}.parquet")
            df.to_parquet(file_path)
            self.logger.info(f"Saved final batch {batch_count} ({len(df)} rows) -> {file_path}")
            
        self.logger.info(f"Completed {self.platform_name} scraper. Total: {total_extracted} items extracted.")
        return total_extracted
