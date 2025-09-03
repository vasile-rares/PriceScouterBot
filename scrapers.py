from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse
from webdriver_manager.chrome import ChromeDriverManager
from rapidfuzz import fuzz
import os, random, time


# --- Funcții auxiliare ---
def _match_score(title: str, query: str) -> float:
    """Returnează un scor de similaritate 0..100 între titlu și căutare folosind doar rapidfuzz.

    Folosim o combinație robustă pentru ordine/rumoare: token_set_ratio (ignoră ordine/duplicări)
    și partial_ratio (potriviri parțiale). Întoarcem scorul maxim.
    """
    t = (title or "").lower()
    q = (query or "").lower()
    # token_set_ratio e mai tolerant la cuvinte în plus; partial_ratio ajută la potriviri subșir.
    return max(
        fuzz.token_set_ratio(q, t),
        fuzz.partial_ratio(q, t),
    )


def _build_driver() -> webdriver.Chrome:
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )  # less noisy, less detectable
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Randomize User-Agent a bit to avoid obvious automation signatures
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ]
    chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")

    prefs = {"profile.default_content_setting_values": {"images": 2}}
    chrome_options.add_experimental_option("prefs", prefs)

    # Optional: Proxy support via PROXY_URL=http://host:port or socks5://host:port
    proxy = os.environ.get("PROXY_URL")
    if proxy:
        chrome_options.add_argument(f"--proxy-server={proxy}")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=chrome_options
    )
    driver.set_page_load_timeout(20)
    try:
        driver.execute_cdp_cmd(
            "Network.setBlockedURLs",
            {"urls": ["*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp"]},
        )
        driver.execute_cdp_cmd("Network.enable", {})
        # Hide webdriver flag
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            },
        )
    except Exception:
        pass
    return driver


# --- Throttling & retries ---
_last_hit_per_host: dict[str, float] = {}
_MIN_DELAY_RANGE = (2.0, 5.0)  # seconds; jitter per host


def _throttled_get(driver: webdriver.Chrome, url: str, *, max_retries: int = 2):
    """Get a URL with per-host rate limiting and small random delay, retry on soft-block pages."""
    host = urlparse(url).netloc
    now = time.time()
    last = _last_hit_per_host.get(host, 0)
    min_delay = random.uniform(*_MIN_DELAY_RANGE)
    to_wait = max(0.0, last + min_delay - now)
    if to_wait > 0:
        time.sleep(to_wait)

    for attempt in range(max_retries + 1):
        driver.get(url)
        # Small human-like pause before parsing
        time.sleep(random.uniform(0.5, 1.2))
        html = (driver.page_source or "").lower()
        # crude signals of rate-limiting/captcha pages
        if any(
            x in html
            for x in [
                "captcha",
                "too many requests",
                "temporarily unavailable",
                "high traffic",
                "are you a human",
            ]
        ):
            if attempt < max_retries:
                # backoff
                time.sleep(2.5 * (attempt + 1) + random.random())
                continue
        break

    _last_hit_per_host[host] = time.time()


# --- Funcții site-uri ---
def search_evomag(product_name: str, driver: webdriver.Chrome):
    best_result = None
    best_score = 0.0
    try:
        url = f"https://www.evomag.ro/?sn.q={product_name.replace(' ', '+')}/"
        _throttled_get(driver, url)
        WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div.nice_product_container")
            )
        )
        products = driver.find_elements(By.CSS_SELECTOR, "div.nice_product_container")
        for p in products:
            try:
                # Titlu
                title = p.find_element(By.CSS_SELECTOR, "div.npi_name a").text.strip()
                score = _match_score(title, product_name)
                if score < 60:  # prag minim pentru relevanță
                    continue

                # Preț
                price = None
                try:
                    price_text = (
                        p.find_element(By.CSS_SELECTOR, "span.real_price")
                        .text.replace("lei", "")
                        .replace("\u00a0", "")
                        .replace(".", "")
                        .replace(",", ".")
                    )
                    price = float(price_text)
                except Exception:
                    pass

                # Link
                link = None
                try:
                    link = p.find_element(
                        By.CSS_SELECTOR, "div.npi_name a"
                    ).get_attribute("href")
                except Exception:
                    pass

                if score > best_score and price and link:
                    best_result = {"title": title, "price": price, "url": link}
                    best_score = score
                    if best_score >= 95:  # potrivire foarte bună, putem opri
                        break
            except Exception:
                continue
    except Exception:
        pass

    return best_result


def search_pcgarage(product_name: str, driver: webdriver.Chrome):
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
                # Titlu
                title = p.find_element(
                    By.CSS_SELECTOR, "div.product_box_name h2 a"
                ).text.strip()
                score = _match_score(title, product_name)
                if score < 60:
                    continue

                # Preț
                price = None
                try:
                    price_text = (
                        p.find_element(
                            By.CSS_SELECTOR, "div.product_box_price_container p.price"
                        )
                        .text.replace("RON", "")
                        .replace("\u00a0", "")
                        .replace(",", ".")
                    )
                    price = float(price_text)
                except Exception:
                    pass

                # Link
                link = None
                try:
                    link = p.find_element(
                        By.CSS_SELECTOR, "div.product_box_name h2 a"
                    ).get_attribute("href")
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

    return best_result


def search_altex(product_name: str, driver: webdriver.Chrome):
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
                title = p.find_element(
                    By.CSS_SELECTOR, "span.Product-name"
                ).text.strip()
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
                    link = p.find_element(By.CSS_SELECTOR, "a[title]").get_attribute(
                        "href"
                    )
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
    return best_result


def search_vexio(product_name: str, driver: webdriver.Chrome):
    best_result = None
    best_score = 0.0
    try:
        url = f"https://www.vexio.ro/search?q={product_name.replace(' ', '%20')}"
        _throttled_get(driver, url)
        WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "article.product-box")
            )
        )
        products = driver.find_elements(By.CSS_SELECTOR, "article.product-box")
        for p in products:
            try:
                title = p.find_element(By.CSS_SELECTOR, "h2.name a").text.strip()
                score = _match_score(title, product_name)
                if score < 60:
                    continue
                price = None
                try:
                    price_text = (
                        p.find_element(By.CSS_SELECTOR, "div.price-value span")
                        .text.replace("lei", "")
                        .replace("\u00a0", "")
                        .replace(",", ".")
                    )
                    price = float(price_text)
                except Exception:
                    pass
                link = None
                try:
                    link = p.find_element(By.CSS_SELECTOR, "h2.name a").get_attribute(
                        "href"
                    )
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
    return best_result


def search_emag(product_name: str, driver: webdriver.Chrome):
    best_result = None
    best_score = 0.0
    try:
        url = f"https://www.emag.ro/search/{product_name.replace(' ', '%20')}"
        _throttled_get(driver, url)
        WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.card-item"))
        )
        products = driver.find_elements(By.CSS_SELECTOR, "div.card-item")
        for idx, p in enumerate(products):
            try:
                title_elem = p.find_element(By.CSS_SELECTOR, "a.card-v2-title")
                title = title_elem.text.strip()
                score = _match_score(title, product_name)
                if score < 60:
                    continue

                price = None
                try:
                    price_elem = p.find_element(By.CSS_SELECTOR, "p.product-new-price")
                    price_text = (
                        price_elem.text.replace("Lei", "")
                        .replace("lei", "")
                        .replace("\u00a0", "")
                        .replace(",", ".")
                    )
                    price = float(price_text)
                except Exception:
                    pass

                link = None
                try:
                    link_elem = p.find_element(By.CSS_SELECTOR, "a.js-product-url")
                    link = link_elem.get_attribute("href")
                except Exception:
                    pass

                if score > best_score and price and link:
                    best_result = {"title": title, "price": price, "url": link}
                    best_score = score
                    if best_score >= 95:
                        break

                if idx > 60 and best_result:
                    break
            except Exception:
                continue
    except Exception:
        pass
    return best_result
