"""Scraper settings — adjust selectors and URLs here."""

import os
from dotenv import load_dotenv

load_dotenv()
SCRAPING_BOT_NAME = "E-commerce Scraper"

BASE_URL = os.getenv("ECOMMERCE_SCRAPER_URL")
SHOP_URL = f"{BASE_URL}/shop/"

# Seconds to wait after navigation (increase if pages load slowly)
PAGE_LOAD_DELAY = 2

# Max wait for elements to appear
WAIT_TIMEOUT = 15

# Output files (written relative to this scraper's directory)
OUTPUT_DIR = "output"
OUTPUT_JSON = "products.json"

# CSS selectors — tweak if the site markup changes
SELECTORS = {
    "listing_product_link": "a.woocommerce-LoopProduct-link",
    "listing_product_link_fallback": "a[href*='/product/']",
    "pagination_next": "a.next.page-numbers",
    "product_title": "h1.product_title",
    "product_price": "p.price",
    "product_prices_all": ".woocommerce-Price-amount",
    "product_description": "#tab-description, .woocommerce-Tabs-panel--description",
    "product_category": ".posted_in a",
    "product_image": ".woocommerce-product-gallery__image img.wp-post-image, .woocommerce-product-gallery__image img:not(.emoji):not(.zoomImg)",
    "product_breadcrumb": ".woocommerce-breadcrumb",
    "product_sku": ".sku",
    "product_stock": "p.stock",
    "product_summary": ".summary.entry-summary, .product .summary",
    "variations_form": "form.variations_form",
    "variation_select": "table.variations select",
    "variation_price": ".woocommerce-variation-price .price, .single_variation .price",
    "variation_sku": ".product_meta .sku",
    "variation_stock": "p.stock",
}
