"""
North America Region Pricing Scrapers
Platforms: Amazon US, Walmart, Target, BestBuy
"""

from .base_scraper import BaseScraper
from .africa_scrapers import generic_discover, generic_scrape

class AmazonUSScraper(BaseScraper):
    def __init__(self):
        super().__init__("AmazonUS", "https://www.amazon.com", delay_range=(3.0, 7.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/s?k=electronics", f"{self.base_url}/s?k=kitchen"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)

class WalmartScraper(BaseScraper):
    def __init__(self):
        super().__init__("Walmart", "https://www.walmart.com", delay_range=(4.0, 8.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/cp/electronics", f"{self.base_url}/cp/home"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)

class TargetScraper(BaseScraper):
    def __init__(self):
        super().__init__("Target", "https://www.target.com", delay_range=(3.0, 6.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/c/electronics", f"{self.base_url}/c/clothing"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)

class BestBuyScraper(BaseScraper):
    def __init__(self):
        super().__init__("BestBuy", "https://www.bestbuy.com", delay_range=(3.0, 7.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/site/electronics", f"{self.base_url}/site/computers"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)


if __name__ == "__main__":
    for scraper_class in [AmazonUSScraper, WalmartScraper, TargetScraper, BestBuyScraper]:
        try:
            s = scraper_class()
            s.run_scraper()
        except Exception as e:
            print(f"Error running {scraper_class.__name__}: {e}")
