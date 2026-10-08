# Architektura eksperymentalnego portu Okapi → Python

**Data:** 2026-10-06  
**Zakres:** wyłącznie `filtry-python/`  
**Status:** badanie B+R, bez integracji z runtime

## 1. Cel

Celem nie jest mechaniczne przepisanie klas Java. Celem jest odtworzenie kontraktu filtrów Okapi w Pythonie tak, aby:

- parser formatu był niezależny od JVM,
- filtr emitował semantyczne zdarzenia,
- tekst tłumaczalny był oddzielony od skeletonu,
- inline codes były strukturą, a nie zwykłym tekstem,
- writer mógł deterministycznie odtworzyć dokument,
- zachowanie można było porównać z oryginalnym Okapi.

Okapi opisuje filtr jako strumień `START_DOCUMENT → zawartość → END_DOCUMENT`, z `TEXT_UNIT`, `DOCUMENT_PART`, grupami i opcjonalnymi subdokumentami. citeturn0search2turn0search12

## 2. Warstwy

```text
Dokument źródłowy
      |
      v
[Parser formatu]
      |
      +----> Skeleton / DocumentPart
      |
      +----> TextUnit
                 |
                 v
             TextFragment
             /          \
        tekst            InlineCode
                 |
                 v
          pipeline tłumaczenia
                 |
                 v
        target TextFragment
                 |
                 v
          [Writer / Merge]
                 |
                 v
          dokument wynikowy
```

Okapi opisuje `TextFragment` jako strukturę oddzielającą coded text od listy inline codes; jest to istotne dla integralności dokumentu. citeturn0search10turn0search13

## 3. Kontrakt Markdown

Dla eksperymentu zachowujemy następujące parametry:

| Parametr | Domyślnie | Etap |
|---|---:|---|
| `translate_fenced_code_blocks` | true | zaimplementowany |
| `translate_indented_code_blocks` | true | zaimplementowany |
| `translate_inline_code_blocks` | true | zaimplementowany |
| `translate_image_alt_text` | true | parametr, semantyka do rozszerzenia |
| `translate_urls` | false | parametr, semantyka do rozszerzenia |
| `translate_header_metadata` | false | parametr, semantyka do rozszerzenia |
| `generate_header_anchors` | false | parametr |
| `parse_mdx` | false | parametr |
| `use_code_finder` | false | parametr |

Dokumentacja Okapi potwierdza te wartości domyślne oraz osobne sterowanie blokami fenced, wciętymi i inline. citeturn0search0turn0search3

## 4. Zasada differential testing

Dla każdego przypadku testowego należy uruchamiać:

1. oryginalny filtr Okapi/JVM,
2. port Python,
3. normalizację reprezentacji,
4. porównanie:
   - kolejności eventów,
   - typów zasobów,
   - tekstu źródłowego,
   - liczby i typów inline codes,
   - skeletonu,
   - parametrów,
   - wyniku round-trip.

Nie porównujemy bezpośrednio przypadkowych szczegółów implementacyjnych Javy. Porównujemy kontrakt obserwowalny.

## 5. Kryteria przejścia

Port nie może zastąpić Javy, dopóki nie przejdzie:

- testów eventów,
- testów TextUnit/TextFragment,
- testów inline codes,
- testów skeleton/merge,
- testów parametrów,
- testów Unicode i kodowania,
- testów błędnych dokumentów,
- testów differential względem Okapi,
- reprezentatywnych dokumentów produkcyjnych,
- testów wydajnościowych,
- audytu licencji i pochodzenia kodu.

## 6. Licencja i pochodzenie

Nie kopiujemy kodu implementacyjnego Java do Pythona. Odtwarzamy zachowanie na podstawie publicznej dokumentacji, obserwacji działania i testów. Repozytorium Okapi Framework jest publikowane na Apache 2.0, ale przed redystrybucją jakiegokolwiek portowanego kodu trzeba wykonać osobny audyt źródła i NOTICE. citeturn0search6

## 7. Granica eksperymentu

Katalog `filtry-python/` jest odseparowany od aktywnego runtime. Do czasu spełnienia kryteriów przejścia:

- nie usuwamy JAR-ów,
- nie zmieniamy FilterRegistry,
- nie zmieniamy aktywnego TPlugin,
- nie przełączamy produkcyjnego filtra Markdown,
- nie dodajemy nowych zależności systemowych.

