# Python Filter Core i Filter IR

## Po co istnieją dwa modele

Projekt rozdziela **opis statyczny filtra** od **modelu dokumentu w czasie wykonania**.

- **Filter IR** opisuje rozpoznane właściwości filtra: formaty, rozszerzenia, cechy, parametry, reguły tokenów oraz część dowodów o klasie Java.
- **Python Filter Core** przechowuje zdarzenia, jednostki tłumaczeniowe, markup i skeleton podczas czytania oraz zapisywania dokumentu.

IR może podpowiedzieć generatorowi, jakie funkcje są wymagane, ale sam w sobie nie parsuje dokumentu i nie gwarantuje poprawnego zapisu.

## Lifecycle filtra

Implementacja bazowa znajduje się w `core/filter.py`. Kontrakt jest podzielony na reader, koordynator lifecycle i writer:

```text
Filter.open(source)
    └── Reader.read(source) → iterator Event
              ↓
Filter.has_next() / Filter.next()
              ↓
Writer.write(event)
              ↓
Filter.close()
```

`Reader` z `core/reader/base.py` udostępnia `read(source) -> Iterable[Event]`. `Writer` z `core/writer/base.py` udostępnia `write(event)`. `Filter.run()` przekazuje każde zdarzenie do writera i zamyka stan w `finally`.

To wspólny mechanizm lifecycle, a nie kompletna implementacja dowolnego filtra Okapi. Każdy filtr nadal odpowiada za reguły parsera, wyodrębnianie jednostek, ochronę treści i serializację formatu.

## Model dokumentu

Definicje znajdują się w `core/document/model.py`.

| Model | Znaczenie |
|---|---|
| `Code` | kod inline / chroniony element przenoszony oddzielnie od zwykłego tekstu |
| `Markup` | znacznik strukturalny typu `start`, `end` albo `empty`, wraz z nazwą, atrybutami i danymi |
| `MarkupComponent` | markup ze stabilnym ID komponentu, relacją rodzic–dziecko i identyfikatorem sparowanego elementu |
| `TextFragment` | uporządkowane części tekstowe, kody i markup; opcjonalne metadata/styl |
| `TextUnit` | jednostka tłumaczeniowa z ID, fragmentami źródłowymi, metadanymi i opcjonalnymi niezależnymi `target_fragments` |
| `Skeleton` | treść oraz markup wymagane do odtworzenia dokumentu, ale nieprzekazywane jako zwykły tekst tłumaczenia |

`MarkupComponent.validate_sequence()` sprawdza spójność par start/end przez ID i nazwę elementu. To zabezpieczenie modelu, nie zamiennik testów właściwych dla danego formatu.

**Nie spłaszczaj bez potrzeby** dokumentu do jednego łańcucha znaków. Takie uproszczenie może zgubić granice jednostek, style, hyperlinki, pola, placeholders, elementy chronione i dane writera.

## Zdarzenia dokumentu

`core/events/model.py` definiuje m.in.:

- `START_DOCUMENT`, `END_DOCUMENT`;
- `TEXT_UNIT`;
- `DOCUMENT_PART`;
- `START_GROUP`, `END_GROUP`;
- granice poddokumentów i subfiltrów.

Zdarzenie zawiera typ, zasób i opcjonalny skeleton. Strumień opisuje dokument, a nie tylko widoczne akapity tekstu. Przy porcie należy badać kolejność zdarzeń, zagnieżdżenie grup i elementy, które writer musi odtworzyć.

`core/events/builder.py` zawiera pomocniczy `EventBuilder`, który tworzy dokument, jednostki, grupy i poddokumenty.

## Pola Filter IR

Model znajduje się w `filter_ir/model/filter.py`. `FilterIR` przechowuje:

- `name`, `version`;
- `mime_types`, `extensions`, `features`;
- deklarowane `parameters` i `parameter_rules`;
- `token_rules`;
- `superclass`, `lifecycle_methods`, `framework_contract`, `entry_class`;
- `used_parameters`;
- opcjonalne `java_evidence`.

`ParameterRule` opisuje nazwę, typ (`boolean`, `string`, `integer`, `pattern`) i default. `TokenRule` opisuje typ tokenu/kodu, strategię tagu (`isolated`, `paired`, `document_part`, `text`) i to, czy token jest tłumaczalny.

Walidator IR weryfikuje podstawową spójność pól i reguł. **Poprawny IR nie oznacza kompletnego odkrycia zachowania**: brak wykrytej reguły może oznaczać ograniczenie analizatora, a nie brak funkcji w Okapi.

## Inwarianty implementacji

Każdy filtr powinien jawnie zachowywać:

1. stabilność ID i kolejność jednostek;
2. oddzielenie source i target;
3. znaczniki start/end/empty, ich sparowanie oraz atrybuty;
4. treści chronione i elementy dokumentu nieprzeznaczone do tłumaczenia;
5. metadata, skeleton i relacje niezbędne dla writera;
6. poprawność dokumentu po zapisie oraz jawne błędy dla przypadków nieobsługiwanych.

## Powiązane źródła

- `core/filter.py`
- `core/reader/base.py`
- `core/writer/base.py`
- `core/document/model.py`
- `core/events/model.py`
- `core/events/builder.py`
- `filter_ir/model/filter.py`
- `tests/test_filter_core.py`
- `tests/test_document_model.py`
- `tests/test_event_builder.py`
- `tests/test_filter_ir.py`
