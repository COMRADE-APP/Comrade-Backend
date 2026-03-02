"""
Asia Region Pricing Scrapers
Platforms: AliExpress, Flipkart, Rakuten, Shopee
"""

from .base_scraper import BaseScraper
from .africa_scrapers import generic_discover, generic_scrape

class AliExpressScraper(BaseScraper):
    def __init__(self):
        super().__init__("AliExpress", "https://www.aliexpress.com", delay_range=(3.0, 7.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/category/200003482/consumer-electronics.html"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)

class FlipkartScraper(BaseScraper):
    def __init__(self):
        super().__init__("Flipkart", "https://www.flipkart.com", delay_range=(3.0, 6.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/mobiles", f"{self.base_url}/laptops"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)

class RakutenScraper(BaseScraper):
    def __init__(self):
        super().__init__("Rakuten", "https://www.rakuten.co.jp", delay_range=(3.0, 6.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/category/smartphones"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)

class ShopeeScraper(BaseScraper):
    def __init__(self):
        super().__init__("Shopee", "https://shopee.sg", delay_range=(3.0, 6.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/Mobile-Gadgets"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)


if __name__ == "__main__":
    for scraper_class in [AliExpressScraper, FlipkartScraper, RakutenScraper, ShopeeScraper]:
        try:
            s = scraper_class()
            s.run_scraper()
        except Exception as e:
            print(f"Error running {scraper_class.__name__}: {e}")
