from scrapers import altex_search_best, search_emag_best


if __name__ == "__main__":
    product = input("Introdu numele produsului: ")

    print("\nCel mai bun rezultat pe Altex...")
    altex_result = altex_search_best(product)
    if altex_result:
        print(
            f"{altex_result['title']} - {altex_result['price']} Lei\n{altex_result['url']}"
        )
    else:
        print("Nu s-au găsit produse potrivite pe Altex.")

    print("\nCel mai bun rezultat pe eMAG...")
    emag_result = search_emag_best(product)
    if emag_result:
        print(
            f"{emag_result['title']} - {emag_result['price']} Lei\n{emag_result['url']}"
        )
    else:
        print("Nu s-a găsit niciun produs pe eMAG.")
