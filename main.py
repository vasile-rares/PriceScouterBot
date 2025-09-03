from scrapers import _build_driver, search_altex, search_emag, search_vexio, search_pcgarage

if __name__ == "__main__":
    product = input("Introdu numele produsului: ")

    driver = _build_driver()
    try:
        print("\nCel mai bun rezultat pe PC Garage...")
        pcgarage_result = search_pcgarage(product, driver)
        if pcgarage_result:
            print(f"{pcgarage_result['title']} - {pcgarage_result['price']} Lei\n{pcgarage_result['url']}")
        else:
            print("Nu s-au găsit produse potrivite pe PC Garage.")

        print("\nCel mai bun rezultat pe Vexio...")
        vexio_result = search_vexio(product, driver)
        if vexio_result:
            print(f"{vexio_result['title']} - {vexio_result['price']} Lei\n{vexio_result['url']}")
        else:
            print("Nu s-au găsit produse potrivite pe Vexio.")

        print("\nCel mai bun rezultat pe Altex...")
        altex_result = search_altex(product, driver)
        if altex_result:
            print(f"{altex_result['title']} - {altex_result['price']} Lei\n{altex_result['url']}")
        else:
            print("Nu s-au găsit produse potrivite pe Altex.")

        print("\nCel mai bun rezultat pe eMAG...")
        emag_result = search_emag(product, driver)
        if emag_result:
            print(f"{emag_result['title']} - {emag_result['price']} Lei\n{emag_result['url']}")
        else:
            print("Nu s-au găsit produse potrivite pe eMAG.")
    finally:
        driver.quit()
