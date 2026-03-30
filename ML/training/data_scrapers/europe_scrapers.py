"""
Europe Region Pricing Scrapers
Platforms: Amazon UK, Otto, Zalando, Argos
"""

from .base_scraper import BaseScraper, register_scraper
from .africa_scrapers import generic_discover, generic_scrape

class AmazonUKScraper(BaseScraper):
    def __init__(self):
        super().__init__("AmazonUK", "https://www.amazon.co.uk", delay_range=(3.0, 7.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/b?node=560798", f"{self.base_url}/b?node=11052681"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)

class OttoScraper(BaseScraper):
    def __init__(self):
        super().__init__("Otto", "https://www.otto.de", delay_range=(4.0, 7.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/technik", f"{self.base_url}/mode"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)

class ZalandoScraper(BaseScraper):
    def __init__(self):
        super().__init__("Zalando", "https://www.zalando.com", delay_range=(3.0, 6.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/mens-clothing", f"{self.base_url}/womens-clothing"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)

class ArgosScraper(BaseScraper):
    def __init__(self):
        super().__init__("Argos", "https://www.argos.co.uk", delay_range=(3.0, 6.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/browse/technology", f"{self.base_url}/browse/home-and-furniture"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)


if __name__ == "__main__":
    for scraper_class in [AmazonUKScraper, OttoScraper, ZalandoScraper, ArgosScraper]:
        try:
            s = scraper_class()
            s.run_scraper()
        except Exception as e:
            print(f"Error running {scraper_class.__name__}: {e}")
