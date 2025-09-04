from scrapers import _build_driver, search_altex, search_emag, search_vexio, search_pcgarage, search_evomag

if __name__ == "__main__":
    product = input("Introdu numele produsului: ")

    driver = _build_driver()
    try:
        # print("\nCel mai bun rezultat pe eVoMag...")
        # evomag_result = search_evomag(product, driver)
        # if evomag_result:
        #     print(f"{evomag_result['title']} - {evomag_result['price']} Lei\n{evomag_result['url']}")
        # else:
        #     print("Nu s-au găsit produse potrivite pe eVoMag.")

        print("\nCel mai bun rezultat pe PC Garage...")
        pcgarage_result = search_pcgarage(product, driver)
        if pcgarage_result:
            print(f"{pcgarage_result['title']} - {pcgarage_result['price']} Lei\n{pcgarage_result['url']}")
            specs = pcgarage_result.get("specs")
            if specs:
                # Print a compact summary if available
                attrs = specs.get("attributes")
                if attrs and isinstance(attrs, dict):
                    # show top 5 attributes
                    print("Specificatii (partial):")
                    count = 0
                    for k, v in attrs.items():
                        print(f" - {k}: {v}")
                        count += 1
                        if count >= 5:
                            break
                elif specs.get("specs_text"):
                    print("Specificatii:")
                    lines = specs["specs_text"].splitlines()[0:10]
                    print("\n".join(lines))
        else:
            print("Nu s-au găsit produse potrivite pe PC Garage.")

        # print("\nCel mai bun rezultat pe Vexio...")
        # vexio_result = search_vexio(product, driver)
        # if vexio_result:
        #     print(f"{vexio_result['title']} - {vexio_result['price']} Lei\n{vexio_result['url']}")
        # else:
        #     print("Nu s-au găsit produse potrivite pe Vexio.")

        # print("\nCel mai bun rezultat pe Altex...")
        # altex_result = search_altex(product, driver)
        # if altex_result:
        #     print(f"{altex_result['title']} - {altex_result['price']} Lei\n{altex_result['url']}")
        # else:
        #     print("Nu s-au găsit produse potrivite pe Altex.")

        # print("\nCel mai bun rezultat pe eMAG...")
        # emag_result = search_emag(product, driver)
        # if emag_result:
        #     print(f"{emag_result['title']} - {emag_result['price']} Lei\n{emag_result['url']}")
        # else:
        #     print("Nu s-au găsit produse potrivite pe eMAG.")
    finally:
        driver.quit()
