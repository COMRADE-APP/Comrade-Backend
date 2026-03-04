"""
Oceania Region Pricing Scrapers
Platforms: Catch, Kogan, TheMarket, DickSmith
"""

from .base_scraper import BaseScraper
from .africa_scrapers import generic_discover, generic_scrape

class CatchScraper(BaseScraper):
    def __init__(self):
        super().__init__("Catch", "https://www.catch.com.au", delay_range=(3.0, 6.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/shop/electronics"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)

class KoganScraper(BaseScraper):
    def __init__(self):
        super().__init__("Kogan", "https://www.kogan.com/au/", delay_range=(3.0, 6.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/c/phones-tablets", f"{self.base_url}/c/computers"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)

class TheMarketScraper(BaseScraper):
    def __init__(self):
        super().__init__("TheMarket", "https://themarket.com/nz/", delay_range=(3.0, 6.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/c/electronics", f"{self.base_url}/c/home-living"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)

class DickSmithScraper(BaseScraper):
    def __init__(self):
        super().__init__("DickSmith", "https://www.dicksmith.com.au/", delay_range=(3.0, 6.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/c/phones-tablets"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)


if __name__ == "__main__":
    for scraper_class in [CatchScraper, KoganScraper, TheMarketScraper, DickSmithScraper]:
        try:
            s = scraper_class()
            s.run_scraper()
        except Exception as e:
            print(f"Error running {scraper_class.__name__}: {e}")
