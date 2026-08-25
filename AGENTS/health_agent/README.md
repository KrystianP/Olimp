# MVP analizy wynikow badan

`analizuj_wyniki.py` to lokalny, ostrozny ekstraktor wynikow badan z PDF.
Jest pierwszym modulem przyszlego Health Agenta.

Zasady przejscia od odczytanej liczby do obserwacji i rekomendacji opisuje
[`PROTOKOL_ANALIZY.md`](PROTOKOL_ANALIZY.md). Kod MVP nie powinien samodzielnie
rozszerzac tych zasad.

## Zakres MVP

- odczyt tekstu z PDF przez `pypdf`,
- wykrywanie parametru, wyniku, jednostki i zakresu referencyjnego,
- przypisanie wyniku do numeru strony zrodla,
- ocena jakosci ekstrakcji,
- raport Markdown i dane JSON,
- jawne oznaczenie dokumentow wymagajacych OCR lub recznej kontroli.

MVP nie diagnozuje, nie interpretuje klinicznie, nie zmienia leczenia i nie
zapisuje automatycznie danych do `CORE` ani Todoist. Oryginalne PDF-y pozostaja
zrodlami niemodyfikowanymi.

## Uruchomienie

Najpewniejsze jest uzycie bundlowanego Pythona Codex:

```bash
PYTHON=/Users/krystianpiatek/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
"$PYTHON" AGENTS/health_agent/analizuj_wyniki.py \
  "PROJECTS/forma_zycia/badania/24.08.2026/Raport Zdrowia.pdf"
```

Aby zapisac roboczy raport i ekstrakcje:

```bash
PYTHON=/Users/krystianpiatek/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
"$PYTHON" AGENTS/health_agent/analizuj_wyniki.py \
  "PROJECTS/forma_zycia/badania/24.08.2026/Raport Zdrowia.pdf" \
  --output /tmp/olimp-analiza-badan
```

Skrypt nie zapisuje niczego, gdy nie podano `--output`.

## Wynik MVP

- `analiza.md` — czytelny raport z ostrzezeniami i numerami stron,
- `ekstrakcja.json` — rekordy do przyszlej recznej akceptacji i historii.

Dokument z uszkodzonym tekstem PDF nie powinien byc „naprawiany” przez zgadywanie.
W takim przypadku raport ma wskazac potrzebe OCR albo recznego przepisania i
potwierdzenia danych.
