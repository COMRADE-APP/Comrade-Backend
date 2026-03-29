"""
South America Region Pricing Scrapers
Platforms: MercadoLibre, Americanas, Linio, Falabella
"""

from .base_scraper import BaseScraper, register_scraper
from .africa_scrapers import generic_discover, generic_scrape

class MercadoLibreScraper(BaseScraper):
    def __init__(self):
        super().__init__("MercadoLibre", "https://www.mercadolibre.com", delay_range=(3.0, 6.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/categorias/electronica", f"{self.base_url}/categorias/hogar"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)

class AmericanasScraper(BaseScraper):
    def __init__(self):
        super().__init__("Americanas", "https://www.americanas.com.br", delay_range=(3.0, 6.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/categoria/celulares", f"{self.base_url}/categoria/eletrodomesticos"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)

class LinioScraper(BaseScraper):
    def __init__(self):
        super().__init__("Linio", "https://www.linio.com", delay_range=(3.0, 6.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/c/tecnologia", f"{self.base_url}/c/belleza"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)

class FalabellaScraper(BaseScraper):
    def __init__(self):
        super().__init__("Falabella", "https://www.falabella.com", delay_range=(3.0, 6.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/category/tecnologia", f"{self.base_url}/category/deportes"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)


if __name__ == "__main__":
    for scraper_class in [MercadoLibreScraper, AmericanasScraper, LinioScraper, FalabellaScraper]:
        try:
            s = scraper_class()
            s.run_scraper()
        except Exception as e:
            print(f"Error running {scraper_class.__name__}: {e}")
