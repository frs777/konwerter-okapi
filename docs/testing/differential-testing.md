# Testy różnicowe i round-trip

## Cel

Testy różnicowe mają wykrywać różnice między oryginalnym filtrem Okapi a natywną implementacją Python. Test round-trip ma dodatkowo wykazać, że odczyt i ponowny zapis nie niszczą struktury dokumentu.

Są to dwa odrębne kryteria:
- **differential testing** — czy oba filtry obserwują i reprezentują dokument w zgodny sposób;
- **round-trip testing** — czy dokument po odczycie/zapisie pozostaje semantycznie poprawny i zachowuje wymagane elementy.

## Aktualny komponent porównujący

- `differential/event_normalizer/normalizer.py` normalizuje eventy do struktur słownikowych; konwertuje enumy, dataclasses, tuple/list oraz sortuje klucze słowników.
- `differential/comparator/comparator.py` porównuje znormalizowane sekwencje i zgłasza różnicę liczby eventów lub różnice na poszczególnych pozycjach.
- `differential/reports/report.py` renderuje podstawowy tekstowy raport.

**Ograniczenie obecnej implementacji:** normalizator zapisuje aktualnie `event.type` i `event.resource`. Samo przejście tego porównania nie dowodzi, że sprawdzono każdy aspekt Okapi, jeśli istotne informacje nie występują w tych polach. Przed użyciem jako bramki zgodności należy rozszerzyć porównanie o wszystkie istotne dla formatu pola i kody inline.

## Minimalny zestaw fixture'ów

Dla każdego formatu przygotuj:
1. typowy plik z podstawową treścią;
2. pusty dokument i puste elementy;
3. Unicode, polskie znaki i nietypowe znaki;
4. wiele fragmentów inline, elementy zagnieżdżone i chronione;
5. identyfikatory, metadata, style i atrybuty;
6. granice segmentacji oraz konfiguracje wpływające na ekstrakcję;
7. uszkodzony lub nieobsługiwany przypadek;
8. wieloczęściowy kontener i relacje między zasobami, jeśli format ich używa.

Każdy fixture powinien mieć jawny oczekiwany rezultat lub bazowy zapis wyniku referencyjnego. Fixture nie może wymagać dostępu do danych użytkownika ani zewnętrznej sieci.

## Pola porównania

| Obszar | Co porównywać |
|---|---|
| Lifecycle | początek/koniec dokumentu, kolejność eventów, błędy |
| Jednostki | liczba, kolejność, stabilne ID, źródło, target i state |
| Segmentacja | granice jednostek, części tłumaczalne i chronione |
| Inline | typ kodu, ID, sparowanie, kolejność, zagnieżdżenie, atrybuty |
| Metadata | styl, zasób, identyfikatory i dane potrzebne writerowi |
| Skeleton | części nieprzetłumaczalne potrzebne do odtworzenia pliku |
| Parametry | wynik przy wartościach domyślnych i wybranych ustawieniach |
| Zapis | poprawność składni i struktury, zachowanie relacji/zasobów |

Porównanie powinno normalizować wyłącznie różnice nieistotne dla kontraktu (np. kolejność kluczy w obiekcie JSON). Nie normalizuj różnic, które mogą zmienić zachowanie dokumentu.

## Round-trip

Dla każdej próbki wykonuj co najmniej dwa przebiegi:

1. **Bez zmian:** odczytaj plik i zapisz bez modyfikowania jednostek. Zweryfikuj strukturę, relacje, kody i treść.
2. **Z translacją:** zmień wyłącznie wybrane fragmenty tłumaczalne, zapisz plik, sprawdź, czy zmieniły się tylko dozwolone miejsca i czy dokument nadal daje się otworzyć/parsować.

Wymóg byte-identical zależy od formatu i celu. Gdy serializer legalnie zmienia białe znaki lub kolejność atrybutów, porównuj strukturę semantyczną; gdy wymagana jest ścisła ochrona niezmienionych bajtów, dodaj osobny test dokładnej identyczności.

## Statusy zgodności

- **niebadany** — brak fixture'u lub wyniku porównawczego;
- **badany** — istnieją dane, ale różnice nie zostały sklasyfikowane;
- **częściowy** — znane luki lub porównanie obejmuje tylko część kontraktu;
- **zgodny w zakresie X** — wskazane fixture'y, konfiguracja, pola porównania, komenda i wynik są zapisane;
- **regresja** — wcześniej potwierdzony przypadek przestał przechodzić.

Nigdy nie używaj ogólnego statusu „zgodny” bez określenia zakresu i dowodów.

## Raport testu

Każdy raport powinien zawierać:
- commit lub identyfikator wersji kodu;
- wersję Javy/Okapi i ścieżki zależności (bez sekretów);
- fixture i konfigurację;
- komendę wykonania;
- wynik referencyjny i Python;
- różnice sklasyfikowane jako istotne/nieistotne;
- rezultat round-trip;
- ograniczenia i status zgodności.
