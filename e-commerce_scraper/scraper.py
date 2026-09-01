"""Selenium scraper for WooCommerce product listings."""

import html
import json
import os
import time
from itertools import product
from typing import Any

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from config import (
    OUTPUT_DIR,
    OUTPUT_JSON,
    PAGE_LOAD_DELAY,
    SELECTORS,
    SHOP_URL,
    WAIT_TIMEOUT,
)


def create_driver() -> webdriver.Chrome:
    """Launch Chrome with a visible window (not headless)."""
    options = Options()
    # options.add_argument("--headless=new")  # enable later when ready

    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options,
    )
    import ipdb; ipdb.set_trace()
    driver.maximize_window()
    return driver


def wait_for_page(driver: webdriver.Chrome) -> None:
    """Wait until the main content area is present."""
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
    )
    time.sleep(PAGE_LOAD_DELAY)


def normalize_product_url(url: str) -> str:
    """Strip query params and trailing slashes for deduplication."""
    return url.split("?")[0].rstrip("/")


def get_product_urls_from_listing(soup: BeautifulSoup) -> list[str]:
    """Collect unique product URLs from a shop listing page."""
    urls: set[str] = set()

    for selector in (
        SELECTORS["listing_product_link"],
        SELECTORS["listing_product_link_fallback"],
    ):
        for link in soup.select(selector):
            href = link.get("href", "")
            if "/product/" in href and "add-to-cart" not in href:
                urls.add(normalize_product_url(href))

    return sorted(urls)


def get_next_page_url(soup: BeautifulSoup) -> str | None:
    """Return the next pagination URL, or None if this is the last page."""
    next_link = soup.select_one(SELECTORS["pagination_next"])
    if not next_link:
        return None
    href = next_link.get("href")
    return href if href else None


def collect_all_product_urls(driver: webdriver.Chrome) -> list[str]:
    """Walk every shop page and gather all product URLs."""
    all_urls: set[str] = set()
    current_url = SHOP_URL
    visited_pages: set[str] = set()

    while current_url:
        normalized_page = normalize_product_url(current_url)
        if normalized_page in visited_pages:
            break
        visited_pages.add(normalized_page)

        print(f"Listing page: {current_url}")
        driver.get(current_url)
        wait_for_page(driver)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        page_urls = get_product_urls_from_listing(soup)
        all_urls.update(page_urls)
        print(f"  Found {len(page_urls)} products on this page ({len(all_urls)} total)")

        current_url = get_next_page_url(soup)

    return sorted(all_urls)


def text_or_none(soup: BeautifulSoup, selector: str) -> str | None:
    element = soup.select_one(selector)
    if not element:
        return None
    return element.get_text(" ", strip=True)


def texts_from_selectors(soup: BeautifulSoup, selectors: str, root: BeautifulSoup | None = None) -> list[str]:
    scope = root or soup
    values: list[str] = []
    for selector in selectors.split(","):
        for element in scope.select(selector.strip()):
            text = element.get_text(" ", strip=True)
            if text:
                values.append(text)
    return values


def normalize_wc_variation(raw: dict[str, Any]) -> dict[str, Any]:
    """Map WooCommerce variation JSON to a consistent shape."""
    attributes = raw.get("attributes") or {}
    attribute_labels = []
    for key, value in attributes.items():
        if not value:
            continue
        label = key.replace("attribute_", "").replace("pa_", "")
        attribute_labels.append(f"{label}: {value}")
    image = raw.get("image") or {}

    return {
        "variation_id": raw.get("variation_id"),
        "attributes": attributes,
        "attribute_summary": ", ".join(attribute_labels),
        "price": raw.get("display_price"),
        "regular_price": raw.get("display_regular_price"),
        "sku": raw.get("sku"),
        "in_stock": raw.get("is_in_stock"),
        "stock_quantity": raw.get("max_qty"),
        "image_url": image.get("src") or image.get("url"),
        "price_html": raw.get("price_html"),
        "source": "embedded_json",
    }


def parse_variations_from_form(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """
    WooCommerce variable products embed all variants in data-product_variations.
    This is the fastest path when the site provides it.
    """
    form = soup.select_one(SELECTORS["variations_form"])
    if not form:
        return []

    raw = form.get("data-product_variations")
    if not raw or raw == "false":
        return []

    try:
        variations_data = json.loads(html.unescape(raw))
    except json.JSONDecodeError:
        return []

    if not isinstance(variations_data, list):
        return []

    return [normalize_wc_variation(item) for item in variations_data]


def parse_variant_option_groups(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Read variation dropdown labels/options when embedded JSON is missing."""
    groups: list[dict[str, Any]] = []

    for row in soup.select("table.variations tr"):
        label_element = row.select_one("label")
        select_element = row.select_one("select")
        if not select_element:
            continue

        label = label_element.get_text(" ", strip=True) if label_element else select_element.get("name", "")
        options = []
        for option in select_element.select("option"):
            value = option.get("value", "")
            if not value:
                continue
            options.append({"value": value, "label": option.get_text(" ", strip=True)})

        if options:
            groups.append(
                {
                    "name": select_element.get("name", ""),
                    "label": label,
                    "options": options,
                }
            )

    return groups


def enrich_variants_with_labels(
    variants: list[dict[str, Any]],
    option_groups: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Add human-readable option labels (e.g. Size: 1 Litre) to each variant."""
    label_by_name: dict[str, str] = {}
    option_label_by_value: dict[tuple[str, str], str] = {}

    for group in option_groups:
        name = group.get("name", "")
        label_by_name[name] = group.get("label", name)
        for option in group.get("options", []):
            option_label_by_value[(name, option.get("value", ""))] = option.get("label", "")

    for variant in variants:
        options: dict[str, str] = {}
        for attr_name, attr_value in (variant.get("attributes") or {}).items():
            label = label_by_name.get(attr_name, attr_name.replace("attribute_", "").replace("pa_", ""))
            value_label = option_label_by_value.get((attr_name, attr_value), attr_value)
            options[label] = value_label
        variant["options"] = options

    return variants


def scrape_variants_via_selenium(driver: webdriver.Chrome) -> list[dict[str, Any]]:
    """
  Fallback for variable products that load prices via AJAX after option selection.
  Iterates every combination of variation dropdowns and reads the updated price/SKU.
  """
    select_elements = driver.find_elements(By.CSS_SELECTOR, SELECTORS["variation_select"])
    if not select_elements:
        return []

    option_groups: list[list[tuple[str, str, str]]] = []
    labels: list[str] = []

    for select_element in select_elements:
        select = Select(select_element)
        name = select_element.get_attribute("name") or ""
        label = name.replace("attribute_", "").replace("pa_", "")

        row = select_element.find_element(By.XPATH, "./ancestor::tr")
        label_elements = row.find_elements(By.CSS_SELECTOR, "label")
        if label_elements:
            label = label_elements[0].text.strip() or label

        labels.append(label)
        options = [
            (name, option.get_attribute("value"), option.text.strip())
            for option in select.options
            if option.get_attribute("value")
        ]
        if not options:
            return []
        option_groups.append(options)

    variants: list[dict[str, Any]] = []

    for combination in product(*option_groups):
        attributes: dict[str, str] = {}
        attribute_labels: list[str] = []

        for index, (attr_name, value, option_label) in enumerate(combination):
            select_element = select_elements[index]
            Select(select_element).select_by_value(value)
            attributes[attr_name] = value
            attribute_labels.append(f"{labels[index]}: {option_label}")

        # Allow AJAX price/SKU update after selection
        time.sleep(1)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        summary = soup.select_one(SELECTORS["product_summary"])

        price = None
        if summary:
            price = text_or_none(summary, SELECTORS["variation_price"]) or text_or_none(
                summary, SELECTORS["product_price"]
            )

        variants.append(
            {
                "variation_id": None,
                "attributes": attributes,
                "attribute_summary": ", ".join(attribute_labels),
                "price": price,
                "regular_price": None,
                "sku": text_or_none(soup, SELECTORS["variation_sku"]),
                "in_stock": None,
                "stock_quantity": None,
                "image_url": None,
                "price_html": price,
                "source": "selenium_selection",
            }
        )

    return variants


def build_simple_variant(soup: BeautifulSoup) -> dict[str, Any]:
    """Single-price products are stored as one variant row for consistent output."""
    summary = soup.select_one(SELECTORS["product_summary"])
    price_scope = summary or soup

    return {
        "variation_id": None,
        "attributes": {},
        "attribute_summary": "default",
        "price": text_or_none(price_scope, SELECTORS["product_price"]),
        "regular_price": None,
        "sku": text_or_none(soup, SELECTORS["product_sku"]),
        "in_stock": None,
        "stock_quantity": None,
        "image_url": None,
        "price_html": text_or_none(price_scope, SELECTORS["product_price"]),
        "source": "simple_product",
    }


def extract_product_variants(driver: webdriver.Chrome, soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Try embedded JSON first, then Selenium dropdown iteration, then simple product."""
    variants = parse_variations_from_form(soup)
    if variants:
        return variants

    if soup.select_one(SELECTORS["variations_form"]) or soup.select(SELECTORS["variation_select"]):
        selenium_variants = scrape_variants_via_selenium(driver)
        if selenium_variants:
            return selenium_variants

    return [build_simple_variant(soup)]


def scrape_product_page(driver: webdriver.Chrome, product_url: str) -> dict[str, Any]:
    """Open a single product page and extract fields."""
    driver.get(product_url)
    wait_for_page(driver)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    summary = soup.select_one(SELECTORS["product_summary"])

    categories = [
        element.get_text(" ", strip=True)
        for element in soup.select(SELECTORS["product_category"])
    ]

    image_element = soup.select_one(SELECTORS["product_image"])
    image_url = image_element.get("src") if image_element else None

    variants = extract_product_variants(driver, soup)
    option_groups = parse_variant_option_groups(soup)
    variants = enrich_variants_with_labels(variants, option_groups)
    price_scope = summary or soup

    product: dict[str, Any] = {
        "url": product_url,
        "name": text_or_none(soup, SELECTORS["product_title"]),
        "price": text_or_none(price_scope, SELECTORS["product_price"]),
        "description": text_or_none(soup, SELECTORS["product_description"]),
        "categories": categories,
        "category": categories[0] if categories else None,
        "image_url": image_url,
        "breadcrumb": text_or_none(soup, SELECTORS["product_breadcrumb"]),
        "sku": text_or_none(soup, SELECTORS["product_sku"]),
        "stock": text_or_none(soup, SELECTORS["product_stock"]),
        "has_variants": len(variants) > 1 or variants[0].get("source") != "simple_product",
        "variant_count": len(variants),
        "variants": variants,
        "variant_option_groups": option_groups,
    }

    return product


def scrape_all_products(driver: webdriver.Chrome) -> list[dict[str, Any]]:
    """Collect URLs from all listing pages, then scrape each product."""
    product_urls = collect_all_product_urls(driver)
    print(f"\nScraping {len(product_urls)} products...\n")

    products: list[dict[str, Any]] = []

    for index, product_url in enumerate(product_urls, start=1):
        print(f"[{index}/{len(product_urls)}] {product_url}")
        try:
            product = scrape_product_page(driver, product_url)
            products.append(product)
            print(f"  -> {product.get('name')} ({product.get('variant_count')} variant(s))")
        except TimeoutException:
            print("  -> TIMEOUT — skipped")
        except Exception as exc:
            print(f"  -> ERROR: {exc}")

    return products


def save_results(products: list[dict[str, Any]], scraper_dir: str) -> str:
    """Write scraped data to JSON."""
    output_path = os.path.join(scraper_dir, OUTPUT_DIR)
    os.makedirs(output_path, exist_ok=True)

    json_path = os.path.join(output_path, OUTPUT_JSON)

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(products, file, indent=2, ensure_ascii=False)

    return json_path
