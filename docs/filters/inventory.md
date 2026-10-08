# Inwentaryzacja filtrów Python

## Zasada

Poniższa lista pochodzi z `execution/native_catalog.py` i opisuje filtry zarejestrowane w natywnym katalogu wykonawczym na dzień przeglądu dokumentacji. **Nie jest to deklaracja pełnej zgodności z Okapi.** Zakres zachowania należy potwierdzać przez testy konkretnego formatu.

## Katalog wykonawczy

| Filtr | Rozszerzenia | Tryb wejścia w katalogu | Implementacja |
|---|---|---|---|
| TXT | `.txt` | ścieżka | `filters/txt/filter.py` |
| DOCX | `.docx` | ścieżka | `filters/docx/filter.py` |
| Markdown | `.md`, `.markdown` | tekst | `filters/markdown/filter.py` |
| HTML | `.html`, `.htm`, `.xhtml` | ścieżka | `filters/html.py` |
| JSON | `.json` | tekst | `filters/json/filter.py` |
| YAML | `.yaml`, `.yml` | tekst | `filters/yaml/filter.py` |
| EPUB | `.epub` | ścieżka | `filters/epub/filter.py` |
| XLIFF 1.x | `.xlf`, `.xliff` | tekst | `filters/xliff/filter.py` |
| XLIFF 2.x | `.xlf`, `.xliff` | tekst | `filters/xliff2/filter.py` |

XLIFF 1.x i XLIFF 2.x współdzielą rozszerzenia. Resolver wykorzystuje rozpoznawanie namespace XML, a jawny format lub identyfikator filtra ma pierwszeństwo.

## Co ta lista oznacza

Katalog deklaruje deskryptory filtrów, fabryki oraz sposób przekazania wejścia do backendu. Nie określa pełnej macierzy obsługiwanych opcji Okapi. Nie oznacza też, że każdy format jest już zgodny we wszystkich wariantach.

Przy ocenie implementacji należy sprawdzić osobno:
- parser i warianty składni;
- reguły translatability;
- parametry filtra;
- segmentację;
- protected content i inline codes;
- metadata oraz skeleton;
- zapis, integralność kontenera i round-trip;
- zachowanie dla błędnych danych.

## Priorytet badań

DOCX/OpenXML ma wysoką złożoność strukturalną: wiele części ZIP/XML, relacje, style, pola, hyperlinki, nagłówki i stopki. Należy zachować testy dotyczące tych elementów i używać referencyjnego Okapi do rozstrzygania różnic.

JSON/YAML wymagają parsowania strukturalnego i wyboru wartości tłumaczalnych; nie wystarczy przekazać cały dokument jako jeden tekst. XLIFF wymaga zachowania ID, segmentów, stanów i kodów inline. EPUB wymaga zachowania manifestu, spine, zasobów i integralności ZIP.

Każda zmiana implementacji powinna aktualizować tę macierz oraz testy. Status „zgodny” może zostać nadany wyłącznie dla konkretnego, przetestowanego zakresu.
