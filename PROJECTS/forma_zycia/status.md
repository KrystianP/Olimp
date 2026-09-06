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
- Do czasu potwierdzenia pierwszego udanego uruchomienia workflow i ponownego
  pobrania danych na komputer harmonogramu nie należy opisywać jako aktywnego.
