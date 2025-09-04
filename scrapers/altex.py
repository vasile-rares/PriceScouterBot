from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .utils import _throttled_get, _match_score

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


def search_altex(product_name: str, driver):
    # exact per-query cache first
    if cache_get_for_query is not None:
        cached = cache_get_for_query("altex", product_name)
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
        url = f"https://altex.ro/cauta/?q={product_name.replace(' ', '%20')}"
        _throttled_get(driver, url)
        WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.Products-item"))
        )
        products = driver.find_elements(By.CSS_SELECTOR, "li.Products-item")
        for p in products:
            try:
                title = p.find_element(By.CSS_SELECTOR, "span.Product-name").text.strip()
                score = _match_score(title, product_name)
                if score < 60:
                    continue
                price = None
                try:
                    price_text = (
                        p.find_element(By.CSS_SELECTOR, "span.Price-int")
                        .text.replace("lei", "")
                        .replace("\u00a0", "")
                        .replace(",", ".")
                    )
                    price = float(price_text)
                except Exception:
                    pass
                link = None
                try:
                    link = p.find_element(By.CSS_SELECTOR, "a[title]").get_attribute("href")
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
        if cache_upsert_for_query is not None:
            try:
                cache_upsert_for_query("altex", product_name, best_result)
            except Exception:
                pass
        elif cache_upsert is not None:
            try:
                cache_upsert("altex", best_result)
            except Exception:
                pass
    return best_result
