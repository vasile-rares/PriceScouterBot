import json
import os
import time
import random
from typing import List, Dict, Any
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# ------------------- Driver -------------------
def build_driver() -> webdriver.Chrome:
    opts = Options()
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
    driver.set_page_load_timeout(35)
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            },
        )
    except Exception:
        pass
    return driver


# ------------------- Parsing -------------------
def parse_price(text: str) -> float | None:
    if not text:
        return None
    t = (
        text.replace("\u00a0", "")
        .replace("LEI", "")
        .replace("Lei", "")
        .replace("lei", "")
        .replace(",", ".")
        .strip()
    )
    cleaned = "".join(ch for ch in t if ch.isdigit() or ch == ".")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except Exception:
        return None


# ------------------- Crawling -------------------
def safe_get(
    driver: webdriver.Chrome, url: str, retries: int = 2, wait_after: float = 0.6
) -> None:
    last_exc = None
    for attempt in range(retries + 1):
        try:
            driver.get(url)
            time.sleep(wait_after)
            return
        except Exception as e:
            last_exc = e
            time.sleep(1.0 + attempt)
    if last_exc:
        raise last_exc


def crawl_page(driver: webdriver.Chrome, url: str) -> List[Dict[str, Any]]:
    safe_get(driver, url)
    try:
        WebDriverWait(driver, 12).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
    except Exception:
        pass
    items = driver.find_elements(By.CSS_SELECTOR, "li.Products-item")
    results: List[Dict[str, Any]] = []
    for el in items:
        try:
            title = el.find_element(By.CSS_SELECTOR, "span.Product-name").text.strip()
        except Exception:
            title = None
        try:
            product_url = el.find_element(By.CSS_SELECTOR, "a[title]").get_attribute(
                "href"
            )
        except Exception:
            product_url = None
        try:
            price_val = parse_price(el.find_element(By.CSS_SELECTOR, ".Price").text)
        except Exception:
            try:
                price_val = parse_price(
                    el.find_element(By.CSS_SELECTOR, "span.Price-int").text
                )
            except Exception:
                price_val = None
        if title and product_url:
            results.append({"title": title, "price": price_val, "url": product_url})
    return results


def crawl_listing(
    driver: webdriver.Chrome, base_url: str, max_pages: int = 3
) -> List[Dict[str, Any]]:
    all_items: List[Dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        if page == 1:
            url = base_url
        else:
            if base_url.endswith("/"):
                url = urljoin(base_url, f"p/{page}/")
            else:
                url = urljoin(base_url + "/", f"p/{page}/")
        page_items = crawl_page(driver, url)
        print(f"[Altex] Page {page}: {len(page_items)} items")
        if not page_items:
            break
        all_items.extend(page_items)
        time.sleep(0.8)
    # de-duplicate by URL
    seen = set()
    deduped = []
    for r in all_items:
        key = r.get("url")
        if key and key not in seen:
            deduped.append(r)
            seen.add(key)
    return deduped


# ------------------- Main -------------------
def main():
    # DEFAULT VALUES for direct run
    default_url = "https://altex.ro/tablete/cpl/filtru/"  # URL categorie
    default_pages = 3
    default_output = os.path.join(os.getcwd(), "altex_results.json")

    driver = build_driver()
    try:
        items = crawl_listing(driver, default_url, default_pages)
    finally:
        driver.quit()

    os.makedirs(os.path.dirname(default_output), exist_ok=True)
    with open(default_output, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(items)} items to {default_output}")


if __name__ == "__main__":
    main()
