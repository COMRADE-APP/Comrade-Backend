import os

SCRAPERS = {
    'africa': ['TakealotScraper', 'KongaScraper', 'JumiaEGScraper', 'ZandoScraper'],
    'na': ['AmazonUSScraper', 'WalmartScraper', 'TargetScraper', 'BestBuyScraper'],
    'sa': ['MercadoLibreScraper', 'AmericanasScraper', 'LinioScraper', 'FalabellaScraper'],
    'europe': ['AmazonUKScraper', 'OttoScraper', 'ZalandoScraper', 'ArgosScraper'],
    'asia': ['AliExpressScraper', 'FlipkartScraper', 'RakutenScraper', 'ShopeeScraper'],
    'oceania': ['CatchScraper', 'KoganScraper', 'TheMarketScraper', 'DickSmithScraper']
}

base_dir = "c:/Users/Imani/Documents/Comrade/Comrade-Backend/ML/training/data_scrapers"

for region, classes in SCRAPERS.items():
    filepath = os.path.join(base_dir, f"{region}_scrapers.py")
    if os.path.exists(filepath):
        class_list = ", ".join(classes)
        block = f"""

if __name__ == "__main__":
    for scraper_class in [{class_list}]:
        try:
            s = scraper_class()
            s.run_scraper()
        except Exception as e:
            print(f"Error running {{scraper_class.__name__}}: {{e}}")
"""
        with open(filepath, 'a') as f:
            f.write(block)
        print(f"Appended to {region}_scrapers.py")
    else:
        print(f"Missing {filepath}")
