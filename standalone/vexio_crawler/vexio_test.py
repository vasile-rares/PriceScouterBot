import json
import os
import asyncio
import random
from typing import List, Dict, Any
from urllib.parse import urljoin

import cloudscraper
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# -------- Selenium pentru extragerea categoriilor --------
def build_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--log-level=3")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )
    opts.add_experimental_option("useAutomationExtension", False)
    prefs = {"profile.default_content_setting_values": {"images": 2}}
    opts.add_experimental_option("prefs", prefs)
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ]
    opts.add_argument(f"--user-agent={random.choice(user_agents)}")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=opts
    )
    driver.set_page_load_timeout(15)
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"},
        )
    except Exception:
        pass
    return driver

def get_main_categories(driver: webdriver.Chrome) -> List[str]:
    driver.get("https://www.vexio.ro/")
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "li.lvl1 a"))
        )
    except Exception:
        return []

    links = driver.find_elements(By.CSS_SELECTOR, "li.lvl1 a[href]")
    categories = set()
    for a in links:
        try:
            href = a.get_attribute("href")
            if href and href.startswith("https://www.vexio.ro/"):
                categories.add(href if href.endswith("/") else href + "/")
        except Exception:
            continue
    return sorted(categories)

# -------- Parsing produse --------
def parse_price(text: str) -> float | None:
    if not text:
        return None
    t = text.replace("\u00a0", "").replace("Lei", "").replace("LEI", "").replace("lei", "").strip()

    # eliminăm spațiile și punctele pentru mii
    t = t.replace(" ", "").replace(".", "")

    # înlocuim virgula cu punct pentru float
    t = t.replace(",", ".")

    try:
        return float(t)
    except Exception:
        return None

def get_products_from_html(html: str, base_url: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    products = []
    for el in soup.select("article.product-box"):
        try:
            title_el = el.select_one("h2.name a")
            title = title_el.text.strip()
            product_url = urljoin(base_url, title_el["href"])
        except Exception:
            title, product_url = None, None

        try:
            price_text = el.select_one("div.price strong").text
            price = parse_price(price_text)
        except Exception:
            price = None

        if title and product_url:
            products.append({
                "title": title,
                "price": price,
                "url": product_url
            })
    return products

# -------- Async fetching --------
MAX_CONCURRENT_REQUESTS = 50
RETRY_COUNT = 2
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

progress_counter = 0
progress_lock = asyncio.Lock()

async def fetch_page_async(scraper, url: str, category_url: str):
    global progress_counter
    async with semaphore:
        for attempt in range(RETRY_COUNT):
            try:
                html = await asyncio.to_thread(scraper.get, url)
                html.raise_for_status()
                products = get_products_from_html(html.text, url)
                for p in products:
                    p["category"] = category_url
                async with progress_lock:
                    progress_counter += len(products)
                    print(f"[*] {url} -> Found {len(products)} products | Total processed: {progress_counter}")
                soup = BeautifulSoup(html.text, "lxml")
                next_exists = bool(soup.select_one("li.pagination-next a"))
                return products, next_exists
            except Exception as e:
                print(f"Attempt {attempt+1} failed for {url}: {e}")
                await asyncio.sleep(0.1)
        return [], False

async def crawl_category_async(category_url: str, max_pages: int = 50) -> List[Dict[str, Any]]:
    scraper = cloudscraper.create_scraper()
    all_items = []
    seen_urls = set()

    for page in range(1, max_pages + 1):
        url = category_url if page == 1 else urljoin(category_url, f"pagina{page}/")
        items, next_exists = await fetch_page_async(scraper, url, category_url)

        if not items:
            print(f"[!] No products found on {url}, stopping {category_url}")
            break

        before = len(all_items)
        for p in items:
            if p["url"] not in seen_urls:
                seen_urls.add(p["url"])
                all_items.append(p)
        after = len(all_items)

        # dacă nu s-au adăugat produse noi => STOP
        if after == before:
            print(f"[!] No NEW products at {url}, stopping {category_url}")
            break

        if not next_exists:
            break

    return all_items

# -------- Crawl toate categoriile cu as_completed --------
async def crawl_all_categories_async(categories: List[str], output_file: str) -> List[Dict[str, Any]]:
    tasks = [crawl_category_async(cat, 5000) for cat in categories]
    all_results = []

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("[\n")
        first = True

        for task in asyncio.as_completed(tasks):
            results = await task
            if results:
                all_results.extend(results)
                for item in results:
                    if not first:
                        f.write(",\n")
                    json.dump(item, f, ensure_ascii=False, indent=2)
                    first = False
                f.flush()

        f.write("\n]\n")

    return all_results

# -------- Main --------
def main():
    driver = build_driver()
    try:
        categories = get_main_categories(driver)
        print(f"Found {len(categories)} main categories:")
        for i, c in enumerate(categories, 1):
            print(f"{i}. {c}")
    finally:
        driver.quit()

    output_file = os.path.join(os.getcwd(), "vexio_products_ultrafast.json")
    all_results = asyncio.run(crawl_all_categories_async(categories, output_file))

    print(f"\nSaved {len(all_results)} items to {output_file}")

if __name__ == "__main__":
    main()
