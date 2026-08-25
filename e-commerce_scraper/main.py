BASE_URL = "https://livebetterwithbetty.com/"
PRODUCT_URL = "https://livebetterwithbetty.com/shop/"

SCRAPING_BOT_NAME = "E-commerce Scraper"

import requests
from bs4 import BeautifulSoup

def get_product_data(product_url):
    response = requests.get(product_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup

def get_product_list(product_url):
    response = requests.get(product_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup 

def get_product_data(product_url):
    response = requests.get(product_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup 


if __name__ == "__main__":
    product_url = PRODUCT_URL
    product_list = get_product_list(product_url)
    print(product_list)