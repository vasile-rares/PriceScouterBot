import requests
from bs4 import BeautifulSoup
from itertools import combinations

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
            price_text = price_tag.get_text(strip=True).replace("Lei", "").replace("\u00a0", "").replace(",", ".")
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