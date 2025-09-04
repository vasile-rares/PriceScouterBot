# PriceScouterBot

Un mic utilitar care caută rapid produse pe magazine online (eMAG, PC Garage, Altex, Vexio, eVoMag).

Noutăți:
- Cache local JSON pentru rezultate PC Garage: la prima căutare salvează produsul (titlu, preț, URL) și niște specificații extrase, astfel căutările viitoare cu denumiri similare răspund instant din cache.

Rulare:
1. Pornește scriptul principal și introdu numele produsului.
2. Rezultatele afișează cel mai bun match per site, iar pentru PC Garage pot apărea și câteva specificații.

Fișiere/structură:
- `cache.py` – utilitar pentru cache JSON (data/cache.json)
- `scrapers/` – pachet cu:
	- `utils.py` – driver, throttling, scoruri de potrivire
	- `pcgarage.py`, `emag.py`, `altex.py`, `vexio.py`, `evomag.py` – scrapers pe site-uri
	- `__init__.py` – re-exporturi convenabile
- `main.py` – interfață CLI simplă

Note:
- Specificațiile extrase depind de structura paginii și pot varia. Cache-ul se actualizează la fiecare găsire de rezultat nou/mai bun.