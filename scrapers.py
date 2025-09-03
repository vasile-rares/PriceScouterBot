"""
Scraping helpers for Altex and eMAG.

Functions:
- altex_search_best(product_name): returns best matching Altex product dict
- search_emag_best(product_name): returns best matching eMAG product dict
"""

import requests
from bs4 import BeautifulSoup
from itertools import combinations
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def search_emag_best(product_name):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=chrome_options
    )

    best_result = None
    max_match_count = 0
    search_words = product_name.lower().split()

    try:
        search_url = f"https://altex.ro/cauta/?q={product_name.replace(' ', '%20')}"
        driver.get(search_url)

        WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.Products-item"))
        )

        products = driver.find_elements(By.CSS_SELECTOR, "li.Products-item")
        if not products:
            print("⚠️ Nu s-au găsit produse pe Altex.")
            return None

        for p in products:
            try:
                title_element = p.find_element(By.CSS_SELECTOR, "span.Product-name")
                title = title_element.text.strip()
                title_lower = title.lower()

                match_count = 0
                for r in range(len(search_words), 0, -1):
                    for combo in combinations(search_words, r):
                        if all(word in title_lower for word in combo):
                            match_count = r
                            break
                    if match_count > 0:
                        break

                if match_count == 0:
                    continue

                try:
                    price_element = p.find_element(By.CSS_SELECTOR, "span.Price-int")
                    price_text = (
                        price_element.text.replace("lei", "")
                        .replace("\u00a0", "")
                        .replace(",", ".")
                    )
                    price = float(price_text)
                except:
                    price = None

                try:
                    link_element = p.find_element(By.CSS_SELECTOR, "a[title]")
                    link = link_element.get_attribute("href")
                except:
                    link = None

                if match_count > max_match_count and price and link:
                    best_result = {"title": title, "price": price, "url": link}
                    max_match_count = match_count

            except:
                continue

    finally:
        driver.quit()

    return best_result


def search_emag_best(product_name):
    url = f"https://www.emag.ro/search/{product_name.replace(' ', '%20')}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    best_result = None
    max_match_count = 0
    search_words = product_name.lower().split()

    for item in soup.select(".card-item"):
        title_tag = item.select_one("a.card-v2-title")
        title = title_tag.text.strip() if title_tag else ""
        title_lower = title.lower()

        match_count = 0
        for r in range(len(search_words), 0, -1):
            for combo in combinations(search_words, r):
                if all(word in title_lower for word in combo):
                    match_count = r
                    break
            if match_count > 0:
                break

        if match_count == 0:
            continue

        price_tag = item.select_one("p.product-new-price")
        if price_tag:
            price_text = (
                price_tag.get_text(strip=True)
                .replace("Lei", "")
                .replace("\u00a0", "")
                .replace(",", ".")
            )
            try:
                price = float(price_text)
            except ValueError:
                price = None
        else:
            price = None

        link_tag = item.select_one("a.js-product-url")
        link = link_tag["href"] if link_tag else None

        if price and link and match_count > max_match_count:
            best_result = {"title": title, "price": price, "url": link}
            max_match_count = match_count

    return best_result
