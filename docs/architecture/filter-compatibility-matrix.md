# Macierz implementacji i zgodności filtrów

## Interpretacja statusu

W projekcie należy odróżniać trzy warstwy:

1. **Implementacja istnieje** — kod filtra znajduje się w `filters/`.
2. **Zintegrowano wykonanie** — filtr ma deskryptor/factory w `execution/native_catalog.py` i może być wybrany przez warstwę execution.
3. **Zgodność z Okapi jest potwierdzona** — wskazany zakres konfiguracji, przypadków i właściwości przechodzi testy różnicowe oraz round-trip.

Pierwsze dwie warstwy nie są dowodem trzeciej.

## Katalog wykonawczy

Lista wynika z bieżącego `execution/native_catalog.py`:

| Filtr | ID katalogu | Rozszerzenia | Tryb wejścia | Punkty krytyczne do sprawdzenia |
|---|---|---|---|---|
| TXT | `native.txt` | `.txt` | ścieżka | UTF-8, końcowy newline, puste treści i bajty |
| DOCX | `native.docx` | `.docx` | ścieżka | wiele runów, fields, hyperlinki, style, nagłówki/stopki i relacje ZIP/XML |
| Markdown | `native.markdown` | `.md`, `.markdown` | tekst | inline code, bloki kodu, tabele, listy, linki, front matter i escaping |
| HTML | `native.html` | `.html`, `.htm`, `.xhtml` | ścieżka | DOM, encje, atrybuty, elementy chronione, markup zagnieżdżony i kodowanie |
| JSON | `native.json` | `.json` | tekst | strukturalny dobór wartości, klucze/typy, escaping, zagnieżdżenia |
| YAML | `native.yaml` | `.yaml`, `.yml` | tekst | typy skalarów, komentarze, bloki wieloliniowe, anchors/aliases |
| EPUB | `native.epub` | `.epub` | ścieżka | manifest/spine, XHTML, zasoby, kolejność i integralność archiwum |
| XLIFF 1.2 | `native.xliff` | `.xlf`, `.xliff` | tekst | source/target, trans-unit, stany, notes, inline codes i namespace |
| XLIFF 2.x | `native.xliff2` | `.xlf`, `.xliff` | tekst | wiele segmentów w unit, pc/ph/sc/ec, source/target, metadata i namespace |

XLIFF 1.2 i 2.x współdzielą rozszerzenia. Resolver ma wykonywać content detection po namespace XML, kiedy nie podano jawnego formatu lub ID filtra.

TXT jest natywnym formatem obsługiwanym przez projekt wykonawczy; sam ten fakt nie oznacza, że odpowiada konkretnemu filtrowi Okapi.

## Priorytety badań

| Priorytet | Format/obszar | Dlaczego | Wymagane dowody |
|---|---|---|---|
| P0 | model dokumentu i inline codes | błąd wspólnego modelu wpływa na wiele filtrów | tożsamość kodów, parowanie, kolejność i ochrona treści |
| P0 | DOCX/OpenXML | wieloczęściowy pakiet, relacje, pola, styles i headers/footers | fixture strukturalny, testy pól/stylów/relacji i round-trip |
| P1 | HTML i EPUB | zagnieżdżenie oraz wieloczęściowe zasoby | walidacja DOM/ZIP, protected content i niezmieniona struktura |
| P1 | XLIFF 1.2 i 2.x | tekst źródłowy/target, segmentacja i markup jako dane dokumentu | wiele segmentów, source/target, namespace, stany, inline |
| P1 | JSON | tylko wartości właściwych typów powinny być tłumaczone | parser po zapisie, typy, klucze, escaping i nested objects |
| P2 | YAML | typy, komentarze i zaawansowana składnia | bloki wieloliniowe, anchors/aliases, komentarze i round-trip |
| P2 | Markdown | składnia miesza tekst z chronioną strukturą | reprezentatywny korpus, bloki kodu, listy/tabele/linki i whitespace |

Priorytet oznacza kolejność weryfikacji, a nie stwierdzenie, że dany format jest już poprawny lub błędny.

## Karta zgodności pojedynczego filtra

Przy rozstrzyganiu zgodności zapisuj następujące dane:

| Pole | Wymagana informacja |
|---|---|
| Wersja | JAR, źródła, metadata oraz narzędzia |
| Konfiguracja | parametry, defaulty i badany zakres |
| Corpus | pliki fixture i pokrywane funkcje |
| Ekstrakcja | eventy, ID, source/target, markup, metadata i skeleton |
| Differential | comparator, różnice i zaakceptowane wyjątki |
| Round-trip | stan dokumentu bez zmian i po zmianie targetu |
| Błędy | niepoprawne wejście, brak zależności, nieobsługiwane opcje |
| Dowód wykonania | data, dokładna komenda oraz liczba passed/failed/skipped |
| Ograniczenia | znane luki i przypadki niebadane |

## Dozwolone statusy

- **niebadany** — brak wystarczającej próbki lub wyniku referencyjnego;
- **analizowany** — zbierane są dane statyczne/runtime;
- **częściowy** — część zachowania działa, luki są otwarte;
- **zweryfikowany w zakresie X** — jawny, testowany podzbiór formatu przeszedł weryfikację;
- **regresja** — przypadek wcześniej zweryfikowany przestał przechodzić.

Nie używaj ogólnego statusu „pełna zgodność” bez zdefiniowanego zakresu parametrów, fixture i dowodów zapisu.
