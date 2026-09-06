# Aktualny status projektu Forma Życia

## Aktualizacja: 11.08.2026

- **Fakt potwierdzony deklaracją Krystiana:** nie spożywa alkoholu od 13.07.2026.
- **Bieżąca reguła:** abstynencja od alkoholu. Plan zdrowotny, wyjazdy i wieczorne procedury mają ją wspierać, a nie zakładać kontrolowane picie.
- **Granica wiedzy:** projekt nie ma danych o wcześniejszej ilości ani częstotliwości spożycia. Nie należy ich dopowiadać ani retrospektywnie oceniać.
- **Przy zmianie stanu:** jednorazowe spożycie lub powrót do alkoholu należy odnotować rzeczowo wraz z sytuacją i następnym krokiem; bez karania dietą lub treningiem.

## Granica aktualności migracji: 19.08.2026

Powyższy stan został przeniesiony bez zmiany znaczenia. W ramach migracji nie
sprawdzano aktualnych zadań w Todoist ani nie wyliczano nowego trendu z danych.
Przed kolejnym planem należy odczytać bieżące zadania i aktualne pomiary.

## Automatyzacja Garmin — stan na 06.09.2026

- Lekki indeks `DATA/garmin/aktywnosci.csv` zawiera 1991 unikalnych
  aktywności z okresu 04.09.2021–06.09.2026. Nie zawiera GPS, identyfikatorów
  urządzeń, ścieżek absolutnych ani surowych plików FIT.
- Lokalna sesja Garmin oraz ręczna synchronizacja aktywności i wagi zostały
  potwierdzone. `DATA/waga.csv` zawiera pomiar dzienny z 06.09.2026.
- Próba uruchomienia przez macOS `launchd` zakończyła się kodem `127`: system
  odmówił `/bin/zsh` otwarcia skryptu w chronionym katalogu `Documents`.
  Niedziałające LaunchAgenty zostały odinstalowane i nie generują błędów w tle.
- Krystian zatwierdził przejście na GitHub Actions: aktywności cztery razy
  dziennie, a waga o 10:00 i 17:00 czasu `Europe/Warsaw`. Mechanizm pozostaje
  niezależny od wykresu; komputer pobiera dane osobnym, bezpiecznym
  fast-forward przy rozpoczęciu lokalnej pracy.
- Workflow GitHub Actions jest aktywny. Końcowy test `34054091261` z
  06.09.2026, wykonany na `actions/checkout@v7` i `actions/setup-python@v7`,
  zakończył się sukcesem: odczytał 27 aktywności i 14 pomiarów wagi; nie
  utworzył commita, ponieważ kanoniczne CSV były już aktualne. Pierwszy bieg
  wywołany harmonogramem pozostaje osobnym potwierdzeniem automatycznego
  wyzwalania.
- Wybór zakresu w harmonogramie porównywał wcześniej bieżącą godzinę z
  rozkładem co do minuty. Kolejka GitHuba opóźnia biegi o kilkanaście minut,
  więc taki warunek pomijałby niemal każde uruchomienie, kończąc je sukcesem
  bez pobrania danych. Od 06.09.2026 o zakresie decyduje wpis crona, który
  wyzwolił bieg; zegar rozstrzyga już tylko czas letni albo zimowy.
- Weryfikacja historii biegów z 06.09.2026: ostatni bieg wywołany
  harmonogramem pochodzi z 27.08.2026 i zakończył się sukcesem, ustawiając
  `run=false`, czyli bez pobrania danych. Wcześniejsze biegi z harmonogramu
  kończyły się na przemian sukcesem bez synchronizacji i błędem przy pustym
  sekrecie `GARMIN_TOKENS_JSON_B64`. Między 28.08 a 05.09.2026 nie ma żadnego
  biegu z harmonogramu; przyczyna tej przerwy pozostaje niepotwierdzona.
  Wniosek: harmonogram nie dostarczył dotąd żadnych danych, a dane w
  repozytorium pochodzą z uruchomień ręcznych.
- Nowa reguła wyboru zakresu została sprawdzona testem
  `automatyzacja/test_harmonogram_workflow.py`, który uruchamia prawdziwy blok
  bash z workflow dla wszystkich 12 wpisów crona w czasie letnim i zimowym.
  Każdy wpis uruchamia się dokładnie w jednej strefie, co daje cztery
  synchronizacje aktywności i dwie wagi na dobę. Potwierdzenie działania na
  produkcji nadal wymaga pierwszego biegu wywołanego harmonogramem.
- Token lokalny został utworzony 06.09.2026 i tę datę przyjmujemy za wiek
  sekretu `GARMIN_TOKENS_JSON_B64`. Sekret nie odnawia się sam: gdy Garmin
  odświeży token, bieg w Actions kończy się ostrzeżeniem i trzeba wykonać
  „Odnawianie tokenu” z `automatyzacja/README.md`. Datę faktycznego odnowienia
  wpisuj w tym miejscu.
