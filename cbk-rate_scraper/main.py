BASE_URL = "https://www.cbk.go.ke/"

SCRAPING_BOT_NAME = "CBK Rate Scraper"

import requests
from bs4 import BeautifulSoup

def get_rate_data(rate_url):
    response = requests.get(rate_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup

def get_rate_list(rate_url):
    response = requests.get(rate_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup

def get_rate_data(rate_url):
    response = requests.get(rate_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup

if __name__ == "__main__":
    rate_url = BASE_URL
    rate_data = get_rate_data(rate_url)
    print(rate_data)