# Krystian OS — Olimp

## Cel systemu

Ten katalog jest samodzielnym systemem kontekstu prywatnego Krystiana. Ma
pomagać zamieniać:

WARTOŚCI → CELE OSOBISTE → PROJEKTY → ZADANIA → DZIAŁANIA → JAKOŚĆ ŻYCIA

System obejmuje zdrowie, badania, sprawność, relacje, rodzinę, pasje, rozwój,
marzenia, podróże oraz finanse osobiste.

## Granica z systemem biznesowym

- Finanse osobiste, poduszka, inwestowanie i prywatne aktywa należą tutaj.
- Przychody, koszty, rentowność i budżety przedsięwzięć należą do systemu
  biznesowego.
- Informacja o pracy może być użyta jako ograniczenie czasu, energii lub
  logistyki, ale ten system nie przechowuje strategii biznesowej.
- Cel zawodowy może być widoczny wyłącznie wtedy, gdy bezpośrednio wpływa na
  ważną decyzję życiową; jego szczegóły pozostają poza tym systemem.

## Źródła prawdy

### `CORE/`

- `profil.md` — trwały kontekst osobisty, zasoby, ograniczenia i styl działania.
- `cele.md` — obowiązujące cele pozazawodowe.
- `zasady.md` — wartości i reguły decyzji życiowych.
- `historia.md` — potwierdzone, istotne zdarzenia i decyzje; nie historia zadań.

### `PROJECTS/`

Każdy aktywny projekt posiada:

- `opis.md` — sens, cel, zakres i ograniczenia,
- `status.md` — aktualny stan, następny rezultat, blokery i decyzje,
- `notatnik.md` — luźne przemyślenia wymagające potwierdzenia aktualności.

`PROJECTS/_szablony/` jest wzorcem tworzenia nowych projektów, a nie aktywnym
projektem.

Aktywne projekty:

- `PROJECTS/forma_zycia/` — zdrowie, redukcja masy ciała, sprawność,
  regeneracja i ciągłość abstynencji.
- `PROJECTS/finanse/` — finanse osobiste, bezpieczeństwo finansowe oraz
  decyzje finansowe i inwestycyjne.
- `PROJECTS/karola/` — relacja partnerska, stabilizacja, wspólny czas i komunikacja.

### `DATA/`

- `waga.csv` — historia pomiarów i średnich masy ciała.
- `nawyki.json` — dane o nawykach, gdy są dostępne.

Nie usuwaj historii pomiarów i nie traktuj pojedynczego odczytu jako diagnozy.

### `AGENTS/` i `.agents/skills/`

- `health_agent/instrukcja.md` — bezpieczne wsparcie zdrowotne.
- `health_agent/analizuj_wyniki.py` — MVP technicznego odczytu wyników badań z
  PDF, z kontrolą jakości i numerami stron źródłowych.
- `health_agent/PROTOKOL_ANALIZY.md` — kolejność analizy i zasady oddzielania
  faktów, obserwacji, hipotez oraz rekomendacji.
- `productivity_agent/instrukcja.md` — planowanie celów i projektów prywatnych.
- `.agents/skills/prowadz-redukcje/` — wyspecjalizowany sposób analizy redukcji.

### Todoist

Todoist jest jedynym źródłem prawdy o zadaniach, terminach, priorytetach i
wykonaniu. Repozytorium przechowuje trwały kontekst i dane, nie kopię zadań.

## Zasady operacyjne

1. Zdrowie i bezpieczeństwo mają pierwszeństwo przed agresywną optymalizacją.
2. Cele konkurują o ograniczony czas; nie aktywuj wszystkiego równocześnie.
3. Pomiar ma prowadzić do decyzji, a nie do moralnej oceny człowieka.
4. Marzenie staje się projektem dopiero po świadomym wyborze rezultatu i
   miejsca w realnym planie.
5. System ma wspierać życie, a nie zastępować jego przeżywanie.
