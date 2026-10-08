# Sprawozdanie B+R — port filtrów Okapi z Javy do Pythona

**Data:** 2026-10-06  
**Etap:** badanie + pierwszy prototyp  
**Status:** częściowy sukces; pełny port nieukończony.

## Cel

Sprawdzić, czy filtry Okapi można odtworzyć w Pythonie bez JVM, bez naruszania aktywnego drzewa aplikacji. Cały eksperyment jest izolowany w `filtry-python/`.

## Stan referencyjny

Lokalny runtime zawiera m.in.:
- `runtime-markdown-1.49.0-SNAPSHOT.jar` — około 72 KiB,
- `okapi-core-1.49.0-SNAPSHOT.jar` — około 664 KiB,
- Flexmark, Jackson, ICU4J, Woodstox, SnakeYAML i Jericho HTML.

Inspekcja bytecode potwierdziła klasę `net.sf.okapi.filters.markdown.MarkdownFilter`.

## Kontrakt Okapi

Markdown Filter posiada m.in. `open()`, `next()`, `hasNext()`, skeleton writer, filter writer, parser Markdown, event builder oraz podfiltry HTML/YAML. Nie jest więc prostym parserem linii.

Dokumentacja Okapi definiuje strumień `START_DOCUMENT → ... → END_DOCUMENT`, w którym mogą występować m.in. `TEXT_UNIT` i `DOCUMENT_PART`. citeturn0search14

## Odkryte parametry domyślne

Bezpośrednia inspekcja `Parameters.reset()` wykazała:

| Parametr | Domyślnie |
|---|---:|
| translateUrls | false |
| translateFencedCodeBlocks | true |
| translateIndentedCodeBlocks | true |
| translateInlineCodeBlocks | true |
| translateHeaderMetadata | false |
| translateImageAltText | true |
| generateHeaderAnchors | false |
| parseMdx | false |
| useCodeFinder | false |

To ważna różnica względem obecnego prostego Pythonowego Markdown Filter.

## Pierwszy port

Utworzono `filtry-python/okapi_markdown_port/` z:
- `markdown_filter.py`,
- `__init__.py`,
- testami,
- README.

Prototyp nie używa Javy ani zewnętrznych zależności. Obsługuje pierwszy wycinek: skeleton, jednostki tekstowe, inline code, linki, obrazy, proste HTML, fenced/indented code i round-trip.

## TDD

Pierwszy cykl miał 1 test RED z powodu błędnego oczekiwania testu: `<b>x</b>` zawiera dwa tagi HTML. Po korekcie: **3 passed**.

Dodane następnie testy zgodności z domyślnymi parametrami Okapi są obecnie RED dla kolejnego etapu implementacji. Nie maskuję tej różnicy.

## Badanie parserów Python

`markdown-it-py` deklaruje zgodność z CommonMark, rozszerzenia/pluginy i bibliotekowy dostęp do parsera. citeturn0search0turn0search5 Wymaga Pythona >=3.10 i ma zależność `mdurl`. citeturn0search11

Mistune 3 oferuje parser, pluginy oraz dostęp do AST, co jest interesujące dla odwzorowania jednostek i skeletonu. citeturn0search2turn0search3 Jest licencjonowany na BSD. citeturn0search2

## Wniosek

**Port jest wykonalny, ale nie jest to mechaniczna konwersja Java → Python.**

Najpierw trzeba odtworzyć:
1. eventy,
2. TextUnit/TextFragment/inline codes,
3. skeleton i merge,
4. parametry filtra,
5. dopiero potem parser Python,
6. testy differential względem Okapi.

Okapi traktuje inline codes jako element pipeline'u filtrów, a nie zwykły tekst. citeturn0search12

## Następny etap

Rozszerzyć Markdown Filter o:
- zgodną konfigurację `Parameters.reset()`,
- pełny minimalny model eventów,
- TEXT_UNIT/DOCUMENT_PART,
- ochronę i odtwarzanie inline codes,
- differential testing tych samych dokumentów względem Okapi,
- później HTML/YAML subfilter.

## Kryterium zastąpienia Javy

Nie usuwamy jeszcze runtime Java. Kandydat Python musi przejść extraction equivalence, inline-code equivalence, skeleton equivalence, round-trip, konfigurację, Unicode/encoding, błędy wejścia i reprezentatywne dokumenty.

**Kryterium nie jest jeszcze spełnione.**


---

# Aktualizacja 2026-10-06 — etap 2

## 13. Research kontraktu Okapi

Oficjalna dokumentacja Okapi potwierdza, że Markdown Filter nie jest prostym parserem linii. Filtr działa w modelu eventowym i może emitować `START_DOCUMENT`, `TEXT_UNIT`, `DOCUMENT_PART`, grupy oraz `END_DOCUMENT`. citeturn0search2

Dokumentacja `TextFragment` potwierdza dodatkowo rozdzielenie tekstu od inline codes. Inline code jest częścią struktury fragmentu, a nie zwykłym tekstem, co pozwala narzędziom tłumaczeniowym zachować markup podczas translacji. citeturn0search10

Dla Markdown oficjalna dokumentacja potwierdza następujące domyślne zachowanie:

- fenced code blocks: tłumaczalne,
- indented code blocks: tłumaczalne,
- inline code blocks: tłumaczalne,
- URL-e: nietłumaczalne domyślnie,
- YAML metadata header: nietłumaczalny domyślnie,
- Code Finder: wyłączony domyślnie.

citeturn0search0turn0search3

Wniosek: port musi odwzorować semantyczny kontrakt, a nie tylko składnię Markdown.

## 14. Wynik TDD

Pierwsza wersja prototypu nie spełniała dwóch nowych testów kontraktowych:

1. brak parametrów konfiguracyjnych,
2. fenced/indented code było zawsze traktowane jako skeleton.

Najpierw dodano testy ujawniające rozbieżność, następnie implementację parametrów i ekstrakcji bloków. Po poprawce:

```text
PYTHONPATH=. python3 -m pytest -q okapi_markdown_port/tests
5 passed

python3 -m compileall -q okapi_markdown_port
PASS
```

Jest to potwierdzenie tylko dla wąskiego kontraktu prototypu.

## 15. Istotna korekta architektoniczna

Podczas implementacji ujawniono, że obecny model `ParsedDocument(lines, units)` jest za prosty, aby wiernie odwzorować pełny kontrakt Okapi.

Powód:

- Okapi rozdziela `TEXT_UNIT` i `DOCUMENT_PART`,
- skeleton nie powinien być utożsamiany z „pominiętą linią”,
- TextUnit posiada TextFragment i związane właściwości,
- inline codes powinny być strukturą,
- writer musi odtwarzać dokument na podstawie zasobów, a nie prostego zastępowania linii.

Dlatego kolejny etap nie będzie polegał na dalszym rozbudowywaniu parsera liniowego. Najpierw zostanie dodany minimalny model eventów i zasobów.

## 16. Licencja

Research wykazał, że publiczne materiały Okapi Framework są dystrybuowane na Apache License 2.0. Nie oznacza to automatycznie, że dowolny port można wykonać przez kopiowanie kodu źródłowego. W tym eksperymencie przyjęto zasadę: **implementacja Python jest niezależną implementacją zachowania, bez kopiowania implementacji Java**. Przed redystrybucją portu wymagany będzie osobny audyt NOTICE, copyright i pochodzenia. citeturn0search6

## 17. Stan decyzji

| Obszar | Stan |
|---|---|
| Wykonalność portu Python | **potwierdzona jako realna hipoteza** |
| Pełna zgodność z Okapi | **niepotwierdzona** |
| JVM można usunąć teraz | **nie** |
| Prototyp Markdown | **działa w izolacji** |
| Testy prototypu | **5 passed** |
| Model eventów | **następny etap** |
| Differential testing JVM ↔ Python | **jeszcze nie wykonany** |
| Integracja z runtime Tłumacza | **brak** |
| Nowe zależności systemowe | **brak** |

## 18. Następny etap B+R

Priorytet:

1. zdefiniować Pythonowe `EventType`,
2. zdefiniować `Event`, `StartDocument`, `TextUnit`, `DocumentPart`, `Ending`,
3. zdefiniować `TextFragment` i strukturalne `InlineCode`,
4. przenieść Markdown Filter na event stream,
5. przygotować fixture'y referencyjne,
6. uruchomić identyczne dokumenty przez Okapi i Python,
7. porównać eventy i round-trip,
8. dopiero potem rozszerzać Markdown o HTML/YAML subfilter,
9. po sukcesie Markdown wybrać drugi filtr o innej klasie trudności.

## 19. Bezpieczeństwo zakresu

Eksperyment pozostaje w:

`/home/frs/Projekty/tlumacz-v4/filtry-python/`

Wykonano backup przed rozszerzeniem:

`backups/okapi-python-rnd-20261006/pre-port-expansion.tar.gz`

SHA-256:

`906cb29b49208078fc0d81fd0de640ac287452934f1f50681b4cb5a7b63e952e`

Nie zmieniono aktywnego Filter Engine, TPlugin, FilterRegistry ani systemowej instalacji Java.


## 20. Etap 3 — minimalny model eventów

Na podstawie oficjalnego Developer Guide dodano eksperymentalny model:

- `EventType.START_DOCUMENT`,
- `EventType.TEXT_UNIT`,
- `EventType.DOCUMENT_PART`,
- `EventType.END_DOCUMENT`,
- `StartDocument`,
- `TextUnit`,
- `DocumentPart`,
- `Ending`,
- `Event`.

Jest to model kontraktu, nie kopia klas Okapi. Oficjalny kontrakt filtrów wymaga co najmniej początku i końca dokumentu, a `TEXT_UNIT` i `DOCUMENT_PART` rozdzielają tekst tłumaczalny od części dokumentu. citeturn0search2

### TDD

Najpierw dodano testy oczekujące modelu eventów. Test zakończył się RED przez brak modułu. Po implementacji:

```text
PYTHONPATH=. python3 -m pytest -q okapi_markdown_port/tests
8 passed

python3 -m compileall -q okapi_markdown_port
PASS
```

Stan 8/8 GREEN obejmuje zarówno wcześniejszy prototyp Markdown, jak i nowy kontrakt eventów.

## 21. Wniosek po etapie eventów

To jest pierwszy dowód, że można budować Pythonowy odpowiednik warstwy Okapi jako własny kontrakt semantyczny.

Nie jest to jeszcze dowód, że można usunąć JVM. Brakuje:

- `TextFragment` z rzeczywistym modelem inline codes,
- skeleton reference/merge,
- event stream emitowanego przez parser Markdown,
- writer'a,
- differential testów z JVM,
- subfiltrów HTML/YAML,
- przypadków błędnych i nietypowych,
- testów na rzeczywistych dokumentach.

## 22. Status B+R

**Faza A — research:** zakończona dla pierwszego przypadku Markdown.

**Faza B — proof of concept:** zakończona częściowo; Markdown + parametry + event contract działają w izolacji.

**Faza C — differential implementation:** rozpoczęta; następny punkt kontrolny to TextFragment/InlineCode i writer.

**Faza D — eliminacja JVM:** nie rozpoczęta i nie powinna być rozpoczęta przed przejściem fazy C.

