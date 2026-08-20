# Forma Życia — migawka danych i kontrakt aktualizacji

Wersja: 2.0
Data migawki: 20 sierpnia 2026
Rola pliku: wersjonowany kontekst dla Projektu ChatGPT, nie żywe źródło danych.

## Zasada nadrzędna

`DATA/waga.csv` jest źródłem historii masy ciała i średnich. Ten plik zapisuje
jedynie migawkę odczytaną 20.08.2026, aby Projekt ChatGPT nie mylił danych z
lipca z danymi bieżącymi. Przy nowszym eksporcie lub deklaracji Krystiana nowa
informacja ma pierwszeństwo; zaproponuj wtedy aktualizację tej migawki.

Oddzielaj:

- **fakt pomiarowy** — ma datę, typ rekordu i źródło;
- **deklarację Krystiana** — ma datę rozmowy;
- **obserwację** — opisuje wzorzec w danych, nie człowieka;
- **hipotezę** — wymaga potwierdzenia;
- **rekomendację** — jest propozycją, nie obowiązującą regułą.

## Ostatnie dane o masie ciała

| Wskaźnik | Wartość | Data/okres | Interpretacja |
|---|---:|---|---|
| Ostatnia średnia tygodniowa | 102,6 kg | 09–15.08.2026 | najnowsza zapisana średnia; −1,1 kg względem poprzedniego zapisanego tygodnia |
| Ostatni pomiar dzienny | 101,7 kg | 16.08.2026 | pojedynczy odczyt; nie zastępuje trendu |
| Cel | 85 kg | do 30.01.2027 | cel z `CORE/cele.md`, nie prognoza |
| Różnica do celu | 17,6 kg | względem średniej 102,6 kg | proste odejmowanie, nie plan tempa |

Źródło: `DATA/waga.csv`, odczyt 20.08.2026. Po 16.08.2026 ta migawka nie ma
nowych pomiarów dziennych; nie twierdź, że opisuje dzisiejszą masę.

## Jakość danych wagi

- CSV ma poprawny schemat i nie zawiera duplikatów rekordów.
- Średnie tygodniowe są lepsze do oceny trendu niż pojedyncze odczyty.
- Historyczne średnie sprzed 18.07.2026 nie zawsze można odtworzyć z zapisanych
  pomiarów dziennych. Traktuj je jako punkty historyczne, nie jako pełną
  podstawę do dokładnych obliczeń tempa.
- Starsze dzienne pomiary z 2025 zawierają podejrzane skoki. Nie używaj ich do
  opowieści o sukcesie, porażce ani tempa redukcji bez jawnej kontroli jakości.
- Zmiana średniej jest zmianą względem poprzedniego **zapisanego** tygodnia;
  przy luce nie oznacza zmiany tydzień-do-tygodnia.

Wniosek opisowy: od 20.06 do 15.08 zapisane średnie spadły z 107,1 kg do
102,6 kg. To nie jest prognoza, ocena zdrowia ani powód do automatycznego
zaostrzania planu.

## Stan zachowań i zdrowia

- **Fakt potwierdzony deklaracją:** abstynencja od alkoholu od 13.07.2026,
  potwierdzona 11.08.2026.
- **Granica wiedzy:** brak danych o wcześniejszej ilości i częstotliwości
  spożycia alkoholu; nie należy ich dopowiadać.
- **Granica wiedzy:** nie ma zapisanych wyników badań, potwierdzenia
  konsultacji lekarskiej, aktualnego obwodu pasa, snu, kroków, treningów ani
  wykonania konkretnych zasad redukcji.
- **Hipoteza do sprawdzenia:** w dokumentacji istnieje niepotwierdzony kontekst
  glukozowo-insulinowy; nie jest diagnozą.

Nie przedstawiaj wieczornego podjadania jako bieżącego faktu bez nowego
potwierdzenia Krystiana. Może być tematem pytania, nie założeniem odpowiedzi.

## Zasady odpowiedzi i przeglądu

1. Nie zmieniaj planu na podstawie jednego pomiaru.
2. Najpierw sprawdź jakość danych i wykonanie uzgodnionych zasad.
3. Jeśli brakuje danych procesu, zapytaj o jedną najważniejszą informację,
   zamiast budować rozbudowany plan.
4. Ustalaj maksymalnie trzy reguły na tydzień; każda wymaga wyzwalacza, reakcji,
   minimalnej wersji, miary i procedury powrotu.
5. Przy objawach alarmowych kieruj do odpowiedniej pomocy medycznej.

## Aktualizacja pakietu ChatGPT

Po pełnym przeglądzie tygodniowym, ważnym wyniku medycznym albo istotnej zmianie
reguł przygotuj nową wersję tego pliku do wgrania do Projektu ChatGPT. Każda
aktualizacja ma zawierać datę, źródło, granicę aktualności oraz rozdzielenie
faktów od rekomendacji. Nie kopiuj tutaj historii zadań z Todoist.
