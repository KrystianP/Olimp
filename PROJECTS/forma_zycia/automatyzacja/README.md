# Synchronizacja Garmin

Automatyzacja zapisuje w Olimp tylko dane potrzebne do celów zdrowotnych i
treningowych. Korzysta z nieoficjalnej biblioteki `garminconnect`, dlatego
każde nieudane logowanie lub zmianę odpowiedzi Garmin należy traktować jako
błąd integracji, a nie dowód braku treningu albo pomiaru.

## Źródła danych

- `DATA/waga.csv` — kanoniczna historia pomiarów i średnich masy ciała;
- `DATA/garmin/aktywnosci.csv` — lekki indeks aktywności, po jednym rekordzie
  na `activity_id`.

Indeks aktywności nie zawiera współrzędnych GPS, identyfikatorów urządzeń,
bezwzględnych ścieżek ani surowych plików FIT. Pełne archiwum z aplikacji
źródłowej nie jest kopiowane do Olimpu. Szczegółowy FIT można pobrać ręcznie
dopiero wtedy, gdy jest potrzebny do analizy konkretnego treningu.

## Dane uwierzytelniające i środowisko

Token Garmina znajduje się poza repozytorium:

```text
~/.config/krystian-os/garmin/garmin_tokens.json
```

Środowisko Python również pozostaje poza repozytorium:

```text
~/Library/Application Support/KrystianOS/garmin/.venv-garmin
```

Hasło nie jest zapisywane. Pierwsze logowanie lub ponowną autoryzację wykonuje
się przez `zaloguj-garmin.command`.

## Harmonogram GitHub Actions

Docelowa synchronizacja działa w prywatnym repozytorium, niezależnie od
wykresu i od tego, czy komputer Krystiana jest włączony:

- aktywności: 06:30, 12:30, 18:30 i 23:30 czasu `Europe/Warsaw`;
- waga: 10:00 i 17:00 czasu `Europe/Warsaw`.

Workflow zapisuje commit tylko wtedy, gdy zmienił się `DATA/waga.csv` albo
`DATA/garmin/aktywnosci.csv`. Token jest przekazywany wyłącznie jako sekret
GitHub `GARMIN_TOKENS_JSON_B64`; nie trafia do repozytorium ani logów.

Każde uruchomienie ponownie sprawdza ostatnie 14 dni. Zapis jest idempotentny:
brak nowych lub poprawionych danych nie zmienia CSV. Wspólna blokada chroni
przed równoległym zapisem obu źródeł.

## Odświeżanie danych na komputerze

`odswiez-dane-z-github.command` jest osobnym mechanizmem i nie zależy od
uruchamiania ani generowania wykresu. Przy rozpoczęciu lokalnej pracy pobiera
`origin/main` i wykonuje wyłącznie fast-forward. Odmawia działania, jeżeli
pliki danych mają lokalne zmiany, bieżąca gałąź nie jest `main` albo historia
lokalna i zdalna są rozbieżne.

Wykres tylko czyta lokalny `DATA/waga.csv`; nie uruchamia synchronizacji.

## Ręczne uruchomienie

```bash
./uruchom-garmin.sh activities
./uruchom-garmin.sh weight
./odswiez-dane-z-github.command
```

Lokalne uruchomienie Garmina służy diagnostyce. Nie powinno działać jako drugi
harmonogram równolegle z GitHub Actions.

## Walidacja

```bash
python3 -m unittest test_synchronizuj_garmin.py
python3 synchronizuj_garmin.py --mode activities --dry-run
python3 synchronizuj_garmin.py --mode weight --dry-run
```

Workflow GitHub Actions wykonuje automatyczne commity i push tylko dla dwóch
kanonicznych plików danych. Lokalny skrypt odświeżający nie tworzy commitów.
