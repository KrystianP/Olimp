# Raport migracji — system prywatny

Data przygotowania: 19.08.2026.

## Cel

Katalog `Priv/` jest samodzielnym kandydatem do przeniesienia do osobnego,
prywatnego repozytorium. Nie zależy od plików z katalogu nadrzędnego ani od
systemu biznesowego.

## Przeniesione źródła

- Osobista część `CORE/profil.md` → `CORE/profil.md`.
- Zdrowie, wyzwania, pasje, relacje i finanse z obowiązującego
  `CORE/cele.md` → `CORE/cele.md`.
- Reguły zdrowotne, osobiste i finansowe → `CORE/zasady.md`.
- Potwierdzony kontekst abstynencji → `CORE/historia.md`.
- Cały śledzony projekt `PROJECTS/forma_zycia/`, w tym materiały kursowe,
  automatyzacja i wykres → `PROJECTS/forma_zycia/`.
- `DATA/waga.csv` i `DATA/nawyki.json` → `DATA/`.
- Workflow Garmin → `.github/workflows/`.
- Skill `prowadz-redukcje` → `.agents/skills/`.
- Wspólne instrukcje i szablony zostały dostosowane do domeny prywatnej.

## Świadomie nieprzeniesione jako aktywne źródła

- `CORE/cele-2.md` i `CORE/cele-3.md`: oba są oznaczone jako propozycje, które
  nie zastąpiły obowiązującego `CORE/cele.md`. Pozostają w repozytorium
  źródłowym do ewentualnego osobnego przeglądu.
- `PROJECTS/ai_brain/`: nie został skopiowany jako aktywny projekt. Jego
  funkcję przejęły instrukcje i szablony repozytorium.
- Ecommerce, profil zawodowy i strategia biznesowa: należą do systemu
  biznesowego.

## Wykluczenia techniczne

Nie kopiowano `.DS_Store`, `.env`, środowiska `.venv-garmin`, cache,
`__pycache__`, `.pytest_cache` ani katalogów roboczych innych narzędzi.

## Todoist

Podczas migracji nie wykonano żadnej zmiany w Todoist. Istniejące ID Forma
Życia pozostało w `opis.md` jako obecne powiązanie dokumentacyjne, ale po
przeniesieniu należy je sprawdzić w aktualnym stanie. Reorganizacja Todoist jest
osobnym, późniejszym etapem wskazanym przez Krystiana.

## Garmin i GitHub

- Kod i workflow zachowują ścieżki względne zgodne z nowym korzeniem repo.
- Skrypt lokalnego logowania ustala repozytorium z bieżącego `git remote`
  zamiast używać starej nazwy `Agenci-AI-2`.
- Po przeniesieniu trzeba skonfigurować remote, sekret
  `GARMIN_TOKENS_JSON_B64` i uruchomić workflow testowo.
- Tokeny i hasła nie zostały skopiowane.

## Warunki gotowości do osobnego repozytorium

- katalog nie zawiera odnośników do plików poza swoim korzeniem,
- dane i materiały Forma Życia są lokalne,
- lokalne środowiska i sekrety są wykluczone,
- system ma własne instrukcje, szablony i reguły Git,
- po przeniesieniu należy zweryfikować Todoist, GitHub Actions i Garmin.
