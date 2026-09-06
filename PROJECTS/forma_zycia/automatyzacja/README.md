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

## Reguły zapisu danych

- Każde uruchomienie ponownie sprawdza ostatnie 14 dni. Zapis jest
  idempotentny: brak nowych lub poprawionych danych nie zmienia CSV.
- Wadliwy rekord z Garmina jest pomijany, a nie przerywa całej synchronizacji.
  Pominięcia trafiają na standardowe wyjście błędów wraz z powodem. Dopiero gdy
  żaden rekord z danego źródła nie nadaje się do zapisu, uruchomienie kończy się
  błędem — cichy brak danych byłby gorszy niż głośna awaria.
- `zmiana_kg` w wierszu dziennym to różnica względem dnia poprzedniego. Powstaje
  tylko wtedy, gdy poprzedni dzień ma pomiar; luka w pomiarach zostawia puste
  pole zamiast różnicy rozpiętej na kilka dni.
- Średnia tygodniowa obejmuje tydzień od niedzieli do soboty i wymaga co
  najmniej trzech pomiarów dziennych. Przeliczane są wszystkie tygodnie
  zamknięte w oknie 14 dni, więc pomiar dosłany z opóźnieniem uzupełnia średnią,
  która wcześniej nie powstała.
- `zmiana_kg` w wierszu tygodniowym powstaje wyłącznie względem tygodnia
  bezpośrednio poprzedzającego. Gdy poprzedni tydzień nie ma średniej, pole
  zostaje puste; liczba rozpięta na dwa tygodnie udawałaby tygodniowy postęp.

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

## Odnawianie tokenu

Token Garmina ma ograniczoną ważność i sam z siebie nie odnowi się w GitHub
Actions. Biblioteka odświeża go w pamięci, ale zapisuje na dysk wyłącznie po
logowaniu hasłem, dlatego skrypt po każdym udanym biegu sam utrwala odświeżony
token lokalnie. Kopia w sekrecie `GARMIN_TOKENS_JSON_B64` pozostaje jednak
migawką z dnia wgrania: maszyna GitHuba znika razem z odświeżonym tokenem.

Gdy skrypt wykryje, że Garmin odświeżył token, wypisuje o tym komunikat, a
workflow zamienia go na ostrzeżenie widoczne w podsumowaniu biegu. **To jest
sygnał, że sekret trzeba odnowić** — nie czekaj na dzień, w którym
synchronizacja zacznie kończyć się błędem `401`.

Odnowienie zajmuje dwa kroki:

```bash
./zaloguj-garmin.command
```

```bash
base64 -i ~/.config/krystian-os/garmin/garmin_tokens.json | tr -d '\n' | gh secret set GARMIN_TOKENS_JSON_B64 --repo KrystianP/Olimp
```

Datę ostatniego wgrania sekretu odnotowuj w `PROJECTS/forma_zycia/status.md`,
żeby wiek tokenu dało się sprawdzić bez logowania do Garmina.

Sam token nigdy nie trafia do logów. Skrypt i workflow posługują się wyłącznie
dwunastoznakowym skrótem, który służy do porównania „ten sam czy inny”.

## Harmonogram GitHub Actions

Docelowa synchronizacja działa w prywatnym repozytorium, niezależnie od
wykresu i od tego, czy komputer Krystiana jest włączony:

- aktywności: 06:30, 12:30, 18:30 i 23:30 czasu `Europe/Warsaw`;
- waga: 10:00 i 17:00 czasu `Europe/Warsaw`.

Każda z tych godzin ma parę wpisów cron w UTC — jeden na czas letni, drugi na
zimowy. O zakresie biegu decyduje **wpis crona, który go wyzwolił**
(`github.event.schedule`), a nie odczyt zegara. Harmonogram GitHuba jest
kolejką i potrafi opóźnić bieg o kilkanaście minut, więc porównywanie bieżącej
godziny z rozkładem pomijałoby prawie każde uruchomienie — i robiłoby to po
cichu, kończąc bieg sukcesem. Zegar rozstrzyga wyłącznie, która połowa pary
letnia/zimowa obowiązuje danego dnia; druga połowa jest pomijana z wyraźnym
komunikatem w logu.

Workflow zapisuje commit tylko wtedy, gdy zmienił się `DATA/waga.csv` albo
`DATA/garmin/aktywnosci.csv`. Token jest przekazywany wyłącznie jako sekret
GitHub `GARMIN_TOKENS_JSON_B64`; nie trafia do repozytorium ani logów. Gdy
commit nie da się przenieść na `origin/main`, rebase jest przerywany, nic nie
zostaje wypchnięte, a bieg kończy się czytelnym błędem.

Równoległe biegi wyklucza grupa `concurrency` po stronie GitHuba. Blokada
plikowa `--lock-file` chroni wyłącznie uruchomienia na komputerze Krystiana:
każdy bieg w Actions dostaje świeżą maszynę, więc nie ma tam czego blokować.

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

`--dry-run` nie zapisuje CSV, ale nadal utrwala odświeżony token: zgubienie go
byłoby dokładnie tą awarią, przed którą chroni ten mechanizm.

Workflow GitHub Actions wykonuje automatyczne commity i push tylko dla dwóch
kanonicznych plików danych. Lokalny skrypt odświeżający nie tworzy commitów.
