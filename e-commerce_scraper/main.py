"""Entry point for the e-commerce product scraper."""

import os

from scraper import create_driver, save_results, scrape_all_products


def main() -> None:
    scraper_dir = os.path.dirname(os.path.abspath(__file__))
    driver = create_driver()

    try:
        products = scrape_all_products(driver)
        json_path = save_results(products, scraper_dir)
        print(f"\nDone — scraped {len(products)} products")
        print(f"  JSON: {json_path}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
