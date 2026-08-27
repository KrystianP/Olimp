# Synchronizacja Garmin do prywatnego repozytorium

Prywatne repozytorium jest kopią danych i kodu potrzebną po zmianie komputera.
Automatyczna synchronizacja GitHub Actions jest obecnie **wyłączona**.
Workflow pozostaje w repozytorium, ale nie uruchamia się według harmonogramu
ani ręcznie, dopóki nie zostanie ponownie włączony w GitHub Actions.

## Dane śledzone przez Git

- `DATA/waga.csv` — historia masy dla istniejącego wykresu;
- `DATA/garmin/garmin.sqlite` — lokalna baza przyszłych aplikacji;
- `DATA/garmin/surowe/aktywnosci/<activity_id>.json` — pełna odpowiedź szczegółów aktywności;
- `DATA/garmin/surowe/oryginalne/<activity_id>.zip` — oryginalny plik aktywności Garmin.

SQLite zawiera szybkie dane do zapytań, natomiast JSON i oryginalne archiwum
chronią przed utratą szczegółów, których aplikacja jeszcze nie wykorzystuje.

## Sekret i ponowne włączenie

Otwórz `zaloguj-garmin.command`. Skrypt wykonuje MFA, a następnie przesyła
odświeżalny token wyłącznie jako sekret GitHub `GARMIN_TOKENS_JSON_B64`.
Hasło i token nie są zapisywane w repozytorium.

Przed wznowieniem synchronizacji trzeba najpierw świadomie włączyć workflow
w zakładce Actions. Pierwsze uruchomienie ręczne domyślnie importuje do 3650
dni wagi i aktywności; później harmonogram odświeża tylko ostatnie 14/30 dni.
Na nowym komputerze wystarczy sklonować repozytorium.

## Zasada backupu

Prywatne GitHub jest repliką danych, ale warto utrzymywać też Time Machine lub
inną niezależną kopię całego folderu repozytorium.
