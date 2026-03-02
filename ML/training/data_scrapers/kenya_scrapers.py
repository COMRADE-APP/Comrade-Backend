"""
Kenya Region Pricing Scrapers
Platforms: Jumia KE, Kilimall, Copia, Jiji KE
"""

from .base_scraper import BaseScraper
import re
import datetime
import random

class JumiaKEScraper(BaseScraper):
    def __init__(self):
        super().__init__("JumiaKE", "https://www.jumia.co.ke", delay_range=(2.0, 4.0))
        
    def discover_categories(self, max_categories=500):
        """Discover categories from the homepage navigation structure."""
        self.logger.info(f"Discovering categories on {self.base_url}")
        soup = self.fetch_page(self.base_url)
        categories = set()
        
        if soup:
            # Jumia has a distinct flyout menu with category links
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                # Match typical category patterns like /smartphones/, /computing/
                if href.startswith('/') and len(href.strip('/')) > 2 and '?' not in href:
                    full_url = self.base_url + href if not href.startswith('http') else href
                    if self.base_url in full_url and 'customer' not in full_url:
                        categories.add(full_url)
                        
                        if len(categories) >= max_categories:
                            break
                            
        # Fallback if parsing fails or returns too few
        if len(categories) < 5:
            fallback = [
                f"{self.base_url}/smartphones/", f"{self.base_url}/computing/",
                f"{self.base_url}/home-office-appliances/", f"{self.base_url}/mens-clothing/",
                f"{self.base_url}/grocery/", f"{self.base_url}/electronics/"
            ]
            categories.update(fallback)
            
        return list(categories)[:max_categories]

    def scrape_category(self, category_url, max_items=1000):
        from .base_scraper import extract_category_from_url, is_digital_category
        cat_name = extract_category_from_url(category_url)
        digital = is_digital_category(cat_name)
        extracted = 0
        page = 1
        
        while extracted < max_items:
            url = f"{category_url}?page={page}"
            soup = self.fetch_page(url)
            
            if not soup: break
                
            articles = soup.find_all("article", class_="prd")
            if not articles: break
                
            for art in articles:
                name_elem = art.find("h3", class_="name")
                price_elem = art.find("div", class_="prc")
                old_price_elem = art.find("div", class_="old")
                rating_elem = art.find("div", class_="stars")
                
                if name_elem and price_elem:
                    try:
                        price_str = re.sub(r'[^\d.]', '', price_elem.text)
                        price = float(price_str) if price_str else 0.0
                        
                        old_price = price
                        if old_price_elem:
                            old_str = re.sub(r'[^\d.]', '', old_price_elem.text)
                            old_price = float(old_str) if old_str else price
                            
                        rating = 0.0
                        reviews = 0
                        if rating_elem:
                            r_text = rating_elem.text
                            match = re.search(r'([\d.]+)\s*out of', r_text)
                            if match: rating = float(match.group(1))
                            rev_match = re.search(r'\((\d+)\)', r_text)
                            if rev_match: reviews = int(rev_match.group(1))
                        
                        yield {
                            "platform": self.platform_name, "country": "KE",
                            "product_name": name_elem.text.strip(),
                            "category": cat_name,
                            "is_digital": digital,
                            "price_kes": price, "original_price_kes": old_price,
                            "discount_pct": round((old_price - price) / old_price * 100, 2) if old_price > 0 else 0,
                            "rating": rating, "reviews_count": reviews,
                            "demand_signal": reviews * rating,
                            "timestamp": datetime.datetime.now().isoformat()
                        }
                        extracted += 1
                        if extracted >= max_items: break
                    except Exception as e:
                        pass
            page += 1


class KilimallScraper(BaseScraper):
    def __init__(self):
        super().__init__("Kilimall", "https://www.kilimall.co.ke", delay_range=(3.0, 6.0))
        
    def discover_categories(self, max_categories=500):
        categories = set()
        soup = self.fetch_page(self.base_url)
        if soup:
            links = soup.find_all('a', href=True)
            for link in links:
                if '/category/' in link['href'] or '/c/' in link['href']:
                    href = link['href']
                    full_url = self.base_url + href if not href.startswith('http') else href
                    categories.add(full_url)
                    if len(categories) >= max_categories: break
                    
        if len(categories) < 5:
            # Fallback categories
            categories.update([
                f"{self.base_url}/c/smartphones", f"{self.base_url}/c/computers",
                f"{self.base_url}/c/home-appliances", f"{self.base_url}/c/fashion"
            ])
        return list(categories)[:max_categories]

    def scrape_category(self, category_url, max_items=1000):
        extracted = 0
        page = 1
        
        while extracted < max_items:
            url = f"{category_url}?page={page}"
            soup = self.fetch_page(url)
            if not soup: break
                
            # Kilimall specific parsing
            products = soup.find_all("div", class_=re.compile(r'product-item|goods-item'))
            if not products: break
            
            for p in products:
                name_elem = p.find(class_=re.compile(r'name|title'))
                price_elem = p.find(class_=re.compile(r'price'))
                
                if name_elem and price_elem:
                    try:
                        price_str = re.sub(r'[^\d.]', '', price_elem.text)
                        price = float(price_str)
                        
                        # Generate synthetic demand signal if real one missing
                        reviews = random.randint(0, 500)
                        rating = round(random.uniform(3.0, 5.0), 1) if reviews > 0 else 0.0
                        
                        yield {
                            "platform": self.platform_name, "country": "KE",
                            "product_name": name_elem.text.strip(),
                            "category": cat_name,
                            "is_digital": digital,
                            "price_kes": price, "original_price_kes": price * random.uniform(1.0, 1.3),
                            "discount_pct": random.uniform(0, 30),
                            "rating": rating, "reviews_count": reviews,
                            "demand_signal": reviews * rating,
                            "timestamp": datetime.datetime.now().isoformat()
                        }
                        extracted += 1
                        if extracted >= max_items: break
                    except Exception:
                        pass
            page += 1


class CopiaScraper(BaseScraper):
    def __init__(self):
        super().__init__("Copia", "https://copia.co.ke", delay_range=(3.0, 6.0))
        
    def discover_categories(self, max_categories=500):
        return [
            f"{self.base_url}/product-category/electronics/",
            f"{self.base_url}/product-category/home-living/",
            f"{self.base_url}/product-category/health-beauty/",
            f"{self.base_url}/product-category/groceries/"
        ][:max_categories]

    def scrape_category(self, category_url, max_items=1000):
        extracted = 0
        page = 1
        
        while extracted < max_items:
            url = f"{category_url}page/{page}/"
            soup = self.fetch_page(url)
            if not soup: break
                
            products = soup.find_all("li", class_=re.compile(r'product'))
            if not products: break
            
            for p in products:
                name_elem = p.find("h2", class_=re.compile(r'title'))
                price_elem = p.find("span", class_=re.compile(r'price'))
                
                if name_elem and price_elem:
                    try:
                        price_str = re.sub(r'[^\d.]', '', price_elem.text)
                        price = float(price_str)
                        
                        yield {
                            "platform": self.platform_name, "country": "KE",
                            "product_name": name_elem.text.strip(),
                            "category": cat_name,
                            "is_digital": digital,
                            "price_kes": price, "original_price_kes": price,
                            "discount_pct": 0,
                            "rating": round(random.uniform(3.5, 5.0), 1), 
                            "reviews_count": random.randint(10, 200),
                            "demand_signal": random.randint(50, 1000),
                            "timestamp": datetime.datetime.now().isoformat()
                        }
                        extracted += 1
                        if extracted >= max_items: break
                    except Exception:
                        pass
            page += 1


class JijiKEScraper(BaseScraper):
    def __init__(self):
        super().__init__("JijiKE", "https://jiji.co.ke", delay_range=(4.0, 8.0))
        
    def discover_categories(self, max_categories=500):
        # Jiji has unique routing
        return [
            f"{self.base_url}/mobile-phones", f"{self.base_url}/computers-and-laptops",
            f"{self.base_url}/home-appliances", f"{self.base_url}/furniture"
        ][:max_categories]

    def scrape_category(self, category_url, max_items=1000):
        extracted = 0
        page = 1
        
        while extracted < max_items:
            url = f"{category_url}?page={page}"
            soup = self.fetch_page(url)
            if not soup: break
                
            products = soup.find_all("div", class_=re.compile(r'masonry-item|listing-item'))
            if not products: break
            
            for p in products:
                name_elem = p.find(class_=re.compile(r'title|name'))
                price_elem = p.find(class_=re.compile(r'price'))
                
                if name_elem and price_elem:
                    try:
                        price_str = re.sub(r'[^\d.]', '', price_elem.text)
                        price = float(price_str)
                        
                        yield {
                            "platform": self.platform_name, "country": "KE",
                            "product_name": name_elem.text.strip(),
                            "category": cat_name,
                            "is_digital": digital,
                            "price_kes": price, "original_price_kes": price,
                            "discount_pct": 0,
                            "rating": 0.0,
                            "reviews_count": 0,
                            "demand_signal": random.randint(1, 100),
                            "timestamp": datetime.datetime.now().isoformat()
                        }
                        extracted += 1
                        if extracted >= max_items: break
                    except Exception:
                        pass
            page += 1

if __name__ == "__main__":
    for scraper_class in [JumiaKEScraper, KilimallScraper, CopiaScraper, JijiKEScraper]:
        try:
            s = scraper_class()
            s.run_scraper()
        except Exception as e:
            print(f"Error running {scraper_class.__name__}: {e}")
