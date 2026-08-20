# Szablony projektów prywatnych

## Rola katalogu

Ten katalog jest wzorcem systemowym używanym przy tworzeniu nowych projektów
osobistych. Nie jest aktywnym projektem i nie ma własnych zadań ani powiązania
z Todoist.

Plik `README.md` jest instrukcją korzystania z szablonów. Pozostaje wyłącznie w
tym katalogu i nie jest kopiowany do nowego projektu.

## Rola poszczególnych plików

- `opis.md` przechowuje trwały sens projektu: dlaczego istnieje, do jakiego
  rezultatu prowadzi, po czym poznamy jego ukończenie, co obejmuje, czego nie
  obejmuje, jakie ma ograniczenia i jakie ma potwierdzone powiązanie z Todoist.
  Zmieniaj go, gdy zmienia się definicja lub kierunek projektu, nie przy każdej
  zmianie bieżącego stanu.
- `status.md` przechowuje zmienny stan projektu: aktualny etap, najbliższy
  rezultat, postęp, blokery i decyzje wpływające na dalszą realizację.
  Aktualizuj go podczas przeglądów i po istotnych zmianach.
- `notatnik.md` służy do datowanych, luźnych przemyśleń. Zasady ich
  interpretacji określa wyłącznie główny `AGENTS.md`.
- Zadania, podzadania, terminy i priorytety przechowuje wyłącznie Todoist.
- Dane pomiarowe i szeregi historyczne należą do `DATA/`, jeśli są potrzebne.

## Pytania startowe

Przed utworzeniem projektu agent wykorzystuje kontekst, który już znajduje się
w systemie i w bieżącej rozmowie. Nie pyta ponownie o informacje już znane ani
nie wymaga odpowiedzi, których nie da się jeszcze udzielić. Brak wiedzy zapisuje
wprost zamiast uzupełniać go założeniem.

Brakujące pytania zadawaj pojedynczo. Kolejne pytanie dobieraj do poprzedniej
odpowiedzi. Po zebraniu odpowiedzi przedstaw Krystianowi krótkie podsumowanie
założeń projektu do sprawdzenia, a następnie wypełnij pliki.

### Pytania do `opis.md`

1. Jak ma nazywać się projekt?
2. Którego obszaru życia dotyczy projekt: zdrowia, relacji, finansów osobistych,
   pasji, rozwoju czy innego obszaru?
3. Dlaczego ten projekt ma istnieć i z jakim celem Krystiana jest związany?
4. Jaki konkretny, obserwowalny rezultat ma powstać dzięki projektowi?
5. Po czym poznamy, że projekt albo jego główny etap został ukończony? Czy ma
   termin lub horyzont czasowy?
6. Co należy do zakresu projektu?
7. Czego projekt świadomie nie obejmuje?
8. Jakie ograniczenia i najważniejsze ryzyka trzeba uwzględnić?
9. Jakie zasady lub granice mają obowiązywać podczas prowadzenia projektu?
10. Czy projekt ma już odpowiednik w Todoist? Jeśli tak, jak się nazywa?

Jeżeli odpowiedź wskazuje, że projekt dotyczy przede wszystkim oferty,
sprzedaży, klientów albo finansów operacyjnych działalności, przerwij tworzenie
w tym systemie i wskaż system biznesowy jako właściwe miejsce.

### Pytania do `status.md`

11. Jaki jest stan początkowy projektu i co zostało już zrobione?
12. Jaki jest najbliższy obserwowalny rezultat, do którego teraz dążymy?
13. Jakie kamienie milowe są już znane i jaki jest ich aktualny stan?
14. Co obecnie blokuje lub może zatrzymać dalszą realizację?
15. Jakie decyzje dotyczące dalszej realizacji zostały już potwierdzone?

### Pytanie do `notatnik.md`

16. Czy są już luźne przemyślenia, pytania lub hipotezy, które Krystian chce
    zapisać w notatniku? Jeśli nie, pozostaw sekcję `Przemyślenia` pustą.

### Pytania dodatkowe tylko w razie potrzeby

- Czy projekt wymaga danych pomiarowych lub historii w `DATA/`?
- Czy projekt wymaga osobnej instrukcji wyspecjalizowanego agenta?
- Czy konkretny rodzaj materiałów uzasadnia utworzenie dodatkowego katalogu?

Nie twórz dodatkowych plików, danych ani instrukcji tylko dlatego, że pytanie
pojawiło się na tej liście. Najpierw musi istnieć konkretna potrzeba.

## Kolejność tworzenia nowego projektu

1. Potwierdź, że Krystian chce uruchomić projekt, a nie tylko zapisać pomysł.
2. Ustal nazwę projektu i bezpieczną nazwę katalogu zapisaną małymi literami,
   bez spacji; do rozdzielania słów użyj podkreśleń.
3. Przeprowadź rozmowę według sekcji `Pytania startowe`, zadając tylko pytania,
   na które nie ma jeszcze odpowiedzi w dostępnym kontekście.
4. Utwórz `PROJECTS/<nazwa_projektu>/`.
5. Na podstawie szablonów utwórz i wypełnij `opis.md`, `status.md` oraz
   `notatnik.md`. Nie kopiuj tego `README.md`.
6. Usuń wszystkie znaczniki `{{...}}` z gotowych plików. Jeśli ważnej
   informacji nie da się potwierdzić, zapisz wprost granicę wiedzy zamiast
   zgadywać.
7. Odszukaj projekt Todoist. ID wpisz do `opis.md` dopiero po potwierdzeniu
   właściwego powiązania. Jeśli projektu nie ma w Todoist, zapytaj Krystiana,
   czy go utworzyć. Dopiero po uzyskaniu zgody utwórz projekt, pobierz jego ID i
   uzupełnij je w `opis.md`.
8. Sprawdź, czy projekt zawiera trzy podstawowe pliki, czy informacje trafiły
   do właściwych miejsc oraz czy `git diff --check` nie zgłasza błędów.

## Zasada lekkości

Nie dodawaj nowych plików, katalogów ani pól na zapas. Rozszerzaj projekt
dopiero wtedy, gdy konkretny rodzaj informacji lub pracy rzeczywiście tego
wymaga.
