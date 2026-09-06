# Przegląd tygodniowy

Stały rytm zamieniający dane na decyzję. Kwadrans, raz w tygodniu, zawsze o tej
samej porze. Przegląd nie jest planowaniem i nie służy do rozbudowy systemu.

## Zasada

System jest gotowy. Brakującym elementem nie był kolejny plik ani skrypt, tylko
stały termin, w którym ktoś patrzy na liczby i podejmuje decyzję. Ten dokument
opisuje ten termin.

## Procedura

1. Uruchom `python3 przeglad.py` w katalogu głównym repozytorium.
2. Przeczytaj wynik. Skrypt podaje liczby, nie rekomendacje.
3. Dla każdego celu z liczbą odpowiedz na jedno pytanie: **czy tempo wystarczy
   do terminu?** Odpowiedź brzmi „tak", „nie" albo „nie wiem, brakuje danych".
4. Gdy tempo nie wystarcza, wybierz jedno z dwóch wyjść i nazwij je wprost:
   zmieniasz działanie albo zmieniasz cel w `CORE/cele.md`. Cel po cichu
   niezrealizowany jest gorszy niż cel jawnie obniżony.
5. Zapisz wynik przeglądu.

## Wyjście przeglądu

Przegląd kończy się dokładnie dwiema rzeczami:

- **maksymalnie 3 zadania w Todoist** na nadchodzący tydzień, każde z
  komentarzem wyjaśniającym powód zgodnie z `AGENTS.md`,
- **jedno zdanie** dopisane do `status.md` właściwego projektu.

Nic więcej. Brak nowych plików, brak nowych projektów, brak zmian w strukturze
repozytorium.

## Limit czasu

Kwadrans. Jeżeli przegląd przekracza ten czas, to znaczy, że zamienił się
w projektowanie. Wtedy przerwij, zapisz trzy zadania z tego, co już wiesz, i
zakończ.

## Zamrożenie systemu

Do **04.10.2026**, czyli przez cztery kolejne przeglądy, repozytorium nie
dostaje nowych funkcji, skryptów, agentów ani projektów.

Jedyny warunek wyjścia z zamrożenia: konkretny przegląd zatrzymał się, bo
**brakowało danych do podjęcia decyzji**. Wtedy wolno dobudować dokładnie to,
czego zabrakło. „Byłoby wygodniej, gdyby…" nie jest podstawą.

Powód zamrożenia jest zapisany w `CORE/profil.md`: uczenie się i planowanie
mogą zastępować wykonanie, a nowe narzędzie potrafi dawać złudzenie
sprawczości.

## Czego przegląd nie robi

- nie diagnozuje i nie ocenia człowieka,
- nie planuje kwartału ani roku,
- nie uruchamia projektów z `CORE/cele.md`,
- nie przenosi wpisów z `notatnik.md` do zadań bez pytania,
- nie rozbudowuje `przeglad.py`.

## Co pokazuje `przeglad.py`

Skrypt czyta `CORE/cele.md`, `DATA/waga.csv` i `DATA/garmin/aktywnosci.csv`.
Statusy i terminy pochodzą z `CORE/cele.md`; cel, który przestał być aktywny,
znika z przeglądu sam.

- cele mierzalne: stan, tempo dotychczasowe i tempo wymagane do terminu,
- licznik abstynencji liczony z deklarowanej daty rozpoczęcia,
- jakość danych: kompletność pomiarów wagi, data ostatniej aktywności i data
  ostatniego pomiaru tkanki tłuszczowej,
- cele aktywne bez miernika, z terminem w najbliższych sześciu miesiącach.

Ostatnia pozycja jest celowa. Cel bez strumienia danych nie da się rozliczyć, a
przegląd ma to pokazywać, zamiast udawać, że wszystko jest mierzone.
