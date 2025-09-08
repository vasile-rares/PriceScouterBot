import json, os, time, random
from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


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
            {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            },
        )
    except Exception:
        pass
    return driver


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


def safe_get(
    driver: webdriver.Chrome, url: str, retries: int = 2, wait_after: float = 0.2
) -> None:
    last_exc = None
    for attempt in range(retries + 1):
        try:
            driver.get(url)
            time.sleep(wait_after)
            return
        except Exception as e:
            last_exc = e
            time.sleep(0.2 + attempt * 0.1)
    if last_exc:
        raise last_exc


def crawl_page(driver: webdriver.Chrome, url: str) -> List[Dict[str, Any]]:
    safe_get(driver, url)
    try:
        WebDriverWait(driver, 3).until(
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
        print(f"[Altex] {url} -> {len(page_items)} items")
        if not page_items:
            break
        all_items.extend(page_items)
        time.sleep(0.05)
    # de-duplicate by URL
    seen = set()
    deduped = []
    for r in all_items:
        key = r.get("url")
        if key and key not in seen:
            deduped.append(r)
            seen.add(key)
    return deduped


def get_main_categories(driver: webdriver.Chrome) -> List[str]:
    safe_get(driver, "https://altex.ro/")
    try:
        WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
    except Exception:
        pass
    links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/cpl/']")
    categories = set()
    for a in links:
        try:
            href = a.get_attribute("href")
            if not href:
                continue
            parsed = urlparse(href)
            parts = [p for p in parsed.path.strip("/").split("/") if p]
            if len(parts) == 2 and parts[1] == "cpl":
                categories.add(href if href.endswith("/") else href + "/")
        except Exception:
            continue
    return sorted(categories)


def main():
    driver = build_driver()
    all_results: List[Dict[str, Any]] = []
    try:
        categories = get_main_categories(driver)
        print(f"Found {len(categories)} main categories:\n")
        for idx, cat in enumerate(categories, 1):
            print(f"{idx}. {cat}")
        print("\n--- Starting crawling ---\n")
        for cat_url in categories:
            print(f"[*] Crawling category: {cat_url}")
            items = crawl_listing(driver, cat_url, max_pages=3)
            for i in items:
                i["category"] = cat_url
            all_results.extend(items)
    finally:
        driver.quit()

    output_file = os.path.join(os.getcwd(), "altex_all_categories.json")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(all_results)} items to {output_file}")


if __name__ == "__main__":
    main()
