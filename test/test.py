import requests

def main():
    url = "https://fenrir.altex.ro/v2/catalog/search/cuptor?size=4"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Afișează numele și prețul produselor
            for product in data.get("products", []):
                print(product.get("name"), "-", product.get("price"))
        else:
            print("Eroare la cerere:", response.status_code)
    except requests.exceptions.RequestException as e:
        print("Eroare la conexiune:", e)

if __name__ == "__main__":
    main()
