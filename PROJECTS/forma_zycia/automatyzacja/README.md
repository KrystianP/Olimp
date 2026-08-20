# Synchronizacja Garmin do prywatnego repozytorium

Prywatne repozytorium jest kopią danych i kodu potrzebną po zmianie komputera.
Synchronizacja GitHub Actions działa codziennie o **23:45** czasu Bratysławy,
również gdy Mac jest wyłączony.

## Dane śledzone przez Git

- `DATA/waga.csv` — historia masy dla istniejącego wykresu;
- `DATA/garmin/garmin.sqlite` — lokalna baza przyszłych aplikacji;
- `DATA/garmin/surowe/aktywnosci/<activity_id>.json` — pełna odpowiedź szczegółów aktywności;
- `DATA/garmin/surowe/oryginalne/<activity_id>.zip` — oryginalny plik aktywności Garmin.

SQLite zawiera szybkie dane do zapytań, natomiast JSON i oryginalne archiwum
chronią przed utratą szczegółów, których aplikacja jeszcze nie wykorzystuje.

## Sekret i pierwszy start

Otwórz `zaloguj-garmin.command`. Skrypt wykonuje MFA, a następnie przesyła
odświeżalny token wyłącznie jako sekret GitHub `GARMIN_TOKENS_JSON_B64`.
Hasło i token nie są zapisywane w repozytorium.

Pierwsze uruchomienie workflow ręcznie w zakładce Actions domyślnie importuje
do 3650 dni wagi i aktywności; później harmonogram odświeża tylko ostatnie
14/30 dni. Na nowym komputerze wystarczy sklonować repozytorium.

## Zasada backupu

Prywatne GitHub jest repliką danych, ale warto utrzymywać też Time Machine lub
inną niezależną kopię całego folderu repozytorium.
