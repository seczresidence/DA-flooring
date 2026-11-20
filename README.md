# Retail Pulse · DATART

Týdenní přehled dostupnosti Samsung a konkurence v prodejnách DATART.

- **Stránka:** https://seczresidence.github.io/retail-pulse/
- **Zdroj dat:** Google Sheet „Flooring“, list `DA_Flooring` (čte se servisním účtem `ffm-download@ffm-kpi.iam.gserviceaccount.com`).
- **Aktualizace:** každé pondělí ve 12:00 (Praha) automaticky. Ručně: záložka **Actions → Update Retail Pulse → Run workflow**.

## Jak to funguje
1. GitHub Actions spustí `scripts/build.py`, který přečte sheet a vloží data do `template.html`.
2. Hotová stránka se nasadí na GitHub Pages. Data se do repozitáře neukládají.
3. Do `last_run.txt` se zapíše čas běhu (udržuje plán aktivní).

Když se nepodaří sheet přečíst nebo se změní hlavička, běh skončí chybou a na webu zůstane poslední dobrá verze. GitHub o chybě pošle e-mail.

## Nastavení
- Secret `GCP_SA_KEY`: celý JSON klíč servisního účtu (Settings → Secrets and variables → Actions).
- Pages: Settings → Pages → Source: **GitHub Actions**.
- Sheet musí být nasdílený se servisním účtem (stačí čtení).

## Pravidla dat
Viz sekce „Data notes“ dole na stránce. Prioritní typy produktů a seznam prodejen (GSCM) jsou v `CONFIG` na začátku skriptu v `template.html`.
