from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def altex_search_names(product_name):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    try:
        search_url = f"https://altex.ro/cauta/?q={product_name.replace(' ', '%20')}"
        driver.get(search_url)

        # Așteaptă până apar produsele (folosim presence_of_all_elements_located)
        WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.Products-item"))
        )

        products = driver.find_elements(By.CSS_SELECTOR, "li.Products-item")
        if not products:
            print("⚠️ Nu s-au găsit produse.")
            return

        for p in products:
            try:
                title_element = p.find_element(By.CSS_SELECTOR, "span.Product-name")
                title = title_element.text.strip()
                print(title)
            except:
                continue

    finally:
        driver.quit()

# Exemplu
altex_search_names("televizor")
