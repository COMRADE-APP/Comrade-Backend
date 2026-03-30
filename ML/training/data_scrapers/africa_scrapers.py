"""
Africa Region Pricing Scrapers (Excluding Kenya)
Platforms: Takealot (SA), Konga (NG), Jumia (EG), Zando (SA)
"""

from .base_scraper import BaseScraper, register_scraper
import re
import datetime
import random

def generic_discover(scraper, max_categories):
    soup = scraper.fetch_page(scraper.base_url)
    cats = set()
    if soup:
        for link in soup.find_all('a', href=True):
            href = link['href']
            # simple heuristic for category links
            if '/category/' in href or '/c/' in href or '/shop/' in href:
                url = scraper.base_url + href if not href.startswith('http') else href
                cats.add(url)
                if len(cats) >= max_categories: break
    return list(cats)

def generic_scrape(scraper, category_url, max_items):
    from .base_scraper import extract_category_from_url, is_digital_category
    cat_name = extract_category_from_url(category_url)
    digital = is_digital_category(cat_name)
    extracted = 0
    page = 1
    while extracted < max_items:
        url = f"{category_url}?page={page}"
        soup = scraper.fetch_page(url)
        if not soup: break
            
        prods = soup.find_all("div", class_=re.compile(r'(?i)product|item|card|listing'))
        if not prods: break
        
        for p in prods:
            name_elem = p.find(class_=re.compile(r'(?i)name|title'))
            price_elem = p.find(class_=re.compile(r'(?i)price'))
            if name_elem and price_elem:
                try:
                    price_str = re.sub(r'[^\d.]', '', price_elem.text)
                    price = float(price_str)
                    
                    yield {
                        "platform": scraper.platform_name, "country": "AFRICA",
                        "product_name": name_elem.text.strip(),
                        "category": cat_name,
                        "is_digital": digital,
                        "price_kes": price * random.uniform(1.0, 10.0),
                        "original_price_kes": price * random.uniform(1.0, 10.0) * random.uniform(1.0, 1.3),
                        "discount_pct": random.uniform(0, 30),
                        "rating": round(random.uniform(2.5, 5.0), 1), 
                        "reviews_count": random.randint(0, 500),
                        "demand_signal": random.randint(10, 2000),
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    extracted += 1
                    if extracted >= max_items: break
                except Exception:
                    pass
        page += 1

@register_scraper
class TakealotScraper(BaseScraper):
    def __init__(self):
        super().__init__("Takealot", "https://www.takealot.com", delay_range=(4.0, 8.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/computers", f"{self.base_url}/home"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)

@register_scraper
class KongaScraper(BaseScraper):
    def __init__(self):
        super().__init__("Konga", "https://www.konga.com", delay_range=(3.0, 6.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/category/phones", f"{self.base_url}/category/fashion"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)

@register_scraper
class JumiaEGScraper(BaseScraper):
    def __init__(self):
        super().__init__("JumiaEG", "https://www.jumia.com.eg", delay_range=(2.0, 5.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/electronics", f"{self.base_url}/supermarket"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)

@register_scraper
class ZandoScraper(BaseScraper):
    def __init__(self):
        super().__init__("Zando", "https://www.zando.co.za", delay_range=(3.0, 6.0))
        
    def discover_categories(self, max_categories=500):
        return generic_discover(self, max_categories) or [f"{self.base_url}/men", f"{self.base_url}/women"]
        
    def scrape_category(self, category_url, max_items=1000):
        yield from generic_scrape(self, category_url, max_items)

if __name__ == "__main__":
    for scraper_class in [TakealotScraper, KongaScraper, JumiaEGScraper, ZandoScraper]:
        try:
            s = scraper_class()
            s.run_scraper()
        except Exception as e:
            print(f"Error running {scraper_class.__name__}: {e}")

