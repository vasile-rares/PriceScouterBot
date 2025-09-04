from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from rapidfuzz import fuzz
from urllib.parse import urlparse
import os, random, time, re
from typing import Dict


# --- Similarity helpers ---
def _match_score(title: str, query: str) -> float:
    t = (title or "").lower()
    q = (query or "").lower()
    return max(
        fuzz.token_set_ratio(q, t),
        fuzz.partial_ratio(q, t),
    )


def _tokenize_words(s: str) -> list[str]:
    tokens = re.split(r"[^\w]+", (s or "").lower())
    stop = {"si", "sau", "de", "la", "cu", "in", "pe", "pentru", "the", "and", "with"}
    return [t for t in tokens if t and t not in stop]


def _token_coverage(title: str, query: str) -> float:
    tset = set(_tokenize_words(title))
    qtok = [w for w in _tokenize_words(query)]
    if not qtok:
        return 0.0
    hit = sum(1 for w in qtok if w in tset)
    return hit / len(qtok)


def _numeric_mismatch_penalty(title: str, query: str) -> int:
    q_nums = set(re.findall(r"\d+", query or ""))
    t_nums = set(re.findall(r"\d+", title or ""))
    penalty = 0
    if q_nums and not q_nums.issubset(t_nums):
        penalty += 25
    extra = t_nums - q_nums
    if extra:
        small = {n for n in extra if len(n) <= 2}
        year_like = {n for n in extra if len(n) == 4}
        if small:
            penalty += 15
        if year_like:
            penalty += 5
    return penalty


def _precise_match_score(title: str, query: str) -> float:
    base = _match_score(title, query)
    cov = _token_coverage(title, query)
    pen = _numeric_mismatch_penalty(title, query)
    score = base * (0.5 + 0.5 * cov) - pen
    return score


# --- WebDriver builder ---
def _build_driver() -> webdriver.Chrome:
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )
    chrome_options.add_experimental_option("useAutomationExtension", False)

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ]
    chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")

    prefs = {"profile.default_content_setting_values": {"images": 2}}
    chrome_options.add_experimental_option("prefs", prefs)

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
_last_hit_per_host: Dict[str, float] = {}
_MIN_DELAY_RANGE = (2.0, 5.0)


def _throttled_get(driver: webdriver.Chrome, url: str, *, max_retries: int = 2):
    host = urlparse(url).netloc
    now = time.time()
    last = _last_hit_per_host.get(host, 0)
    min_delay = random.uniform(*_MIN_DELAY_RANGE)
    to_wait = max(0.0, last + min_delay - now)
    if to_wait > 0:
        time.sleep(to_wait)

    for attempt in range(max_retries + 1):
        driver.get(url)
        time.sleep(random.uniform(0.5, 1.2))
        html = (driver.page_source or "").lower()
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
                time.sleep(2.5 * (attempt + 1) + random.random())
                continue
        break

    _last_hit_per_host[host] = time.time()
