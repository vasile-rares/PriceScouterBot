from typing import Any, Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .utils import _throttled_get, _precise_match_score

try:
    from cache import (
        get_for_query as cache_get_for_query,
        upsert_for_query as cache_upsert_for_query,
        upsert as cache_upsert,
    )
except Exception:
    cache_get_for_query = None
    cache_upsert_for_query = None
    cache_upsert = None


def _extract_pcgarage_specs(product_url: str, driver) -> dict:
    specs: Dict[str, Any] = {}
    try:
        _throttled_get(driver, product_url)
        try:
            title = driver.find_element(By.CSS_SELECTOR, "h1.page-title").text.strip()
            specs["title"] = title
        except Exception:
            pass
        try:
            blocks = driver.find_elements(By.CSS_SELECTOR, "#tab-specs, div#product-specs, div.specs, div#specificatii")
            if blocks:
                texts = []
                for b in blocks:
                    try:
                        texts.append(b.text)
                    except Exception:
                        continue
                if texts:
                    joined = "\n".join(t.strip() for t in texts if t)
                    if joined:
                        specs["specs_text"] = joined[:5000]
        except Exception:
            pass
        try:
            rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
            kv = {}
            for r in rows:
                try:
                    th = r.find_element(By.CSS_SELECTOR, "th, td:nth-child(1)").text.strip()
                    td = r.find_element(By.CSS_SELECTOR, "td:nth-child(2)").text.strip()
                    if th and td:
                        kv[th] = td
                except Exception:
                    continue
            if kv:
                specs["attributes"] = kv
        except Exception:
            pass
    except Exception:
        pass
    return specs


def search_pcgarage(product_name: str, driver):
    # exact per-query cache first
    if cache_get_for_query is not None:
        cached = cache_get_for_query("pcgarage", product_name)
        if cached:
            return {
                "title": cached.get("title"),
                "price": cached.get("price"),
                "url": cached.get("url"),
                "specs": cached.get("specs"),
            }

    best_result = None
    best_score = 0.0
    try:
        url = f"https://www.pcgarage.ro/cauta/{product_name.replace(' ', '+')}/"
        _throttled_get(driver, url)
        WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div.product_b_container")
            )
        )
        products = driver.find_elements(By.CSS_SELECTOR, "div.product_b_container")
        for p in products:
            try:
                title = p.find_element(By.CSS_SELECTOR, "div.product_box_name h2 a").text.strip()
                score = _precise_match_score(title, product_name)
                if score < 60:
                    continue
                price = None
                try:
                    price_text = (
                        p.find_element(By.CSS_SELECTOR, "div.product_box_price_container p.price")
                        .text.replace("RON", "")
                        .replace("\u00a0", "")
                        .replace(",", ".")
                    )
                    price = float(price_text)
                except Exception:
                    pass
                link = None
                try:
                    link = p.find_element(By.CSS_SELECTOR, "div.product_box_name h2 a").get_attribute("href")
                except Exception:
                    pass
                if score > best_score and price and link:
                    best_result = {"title": title, "price": price, "url": link}
                    best_score = score
                    if best_score >= 95:
                        break
            except Exception:
                continue
    except Exception:
        pass

    if best_result:
        try:
            specs = _extract_pcgarage_specs(best_result["url"], driver)
            if specs:
                best_result["specs"] = specs
        except Exception:
            pass
        if cache_upsert_for_query is not None:
            try:
                cache_upsert_for_query("pcgarage", product_name, best_result)
            except Exception:
                pass
        elif cache_upsert is not None:
            try:
                cache_upsert("pcgarage", best_result)
            except Exception:
                pass
    return best_result
