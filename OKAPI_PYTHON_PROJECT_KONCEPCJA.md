# Projekt: Okapi Python — koncepcja niezależnego portu filtrów Okapi

**Status:** koncepcja B+R zatwierdzona do rozpoczęcia prac  
**Data:** 2026-10-06  
**Projekt nadrzędny:** niezależny od „Tłumacza”  
**Cel strategiczny:** wyeliminowanie zależności produkcyjnego przetwarzania dokumentów od Javy/JVM

---

## 1. Decyzja architektoniczna

Projekt powinien zostać wydzielony z repozytorium „Tłumacz” i prowadzony jako **samodzielny projekt badawczo-rozwojowy**.

Powód jest zasadniczy: celem nie jest napisanie kolejnego filtra dla „Tłumacza”, lecz opracowanie **ogólnej, wielokrotnego użytku technologii pozwalającej odtwarzać zachowanie filtrów Okapi w środowisku Python bez JVM**.

„Tłumacz” powinien w przyszłości korzystać z gotowego rezultatu jako konsument:

```text
                    ┌──────────────────────┐
                    │       TŁUMACZ        │
                    │      V4 / V5 ...      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Python Filter Core  │
                    └──────────┬───────────┘
                               │
             ┌─────────────────┼─────────────────┐
             ▼                 ▼                 ▼
        Markdown            HTML             EPUB/DOCX/...
```

Natomiast projekt B+R będzie rozwijany niezależnie:

```text
Okapi Java / JAR
       │
       ▼
┌──────────────────────┐
│ Okapi Filter Analyzer │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│    Filter IR         │
│ Intermediate         │
│ Representation       │
└──────────┬───────────┘
           │
           ├──────────────► analiza / raport
           │
           ▼
┌──────────────────────┐
│ Python Filter Core   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Python Filter        │
│ konkretnego formatu  │
└──────────┬───────────┘
           │
           ▼
     test differential
           │
           ▼
      zgodność z Okapi
```

---

# 2. Problem, który rozwiązujemy

Obecny model Okapi opiera się na wspólnym frameworku oraz implementacjach filtrów dla poszczególnych formatów dokumentów.

Filtr nie jest wyłącznie prostą listą deklaratywnych reguł typu:

> „ten fragment jest tłumaczalny, ten fragment jest chroniony”.

W praktyce filtr implementuje logikę rozpoznawania dokumentu, budowania wspólnego modelu treści, ochrony elementów nietłumaczalnych, tworzenia zdarzeń oraz ponownego zapisu dokumentu.

Oficjalna strona Okapi opisuje framework jako zestaw komponentów wspierających lokalizację i tłumaczenie dokumentacji oraz oprogramowania, z naciskiem na interoperacyjność i otwarte standardy.

W architekturze Okapi filtr pełni rolę adaptera:

```text
FORMAT NATYWNY
      │
      ▼
┌─────────────┐
│   FILTER    │
└──────┬──────┘
       │
       ▼
WSPÓLNY MODEL DOKUMENTU
       │
       ▼
narzędzia tłumaczeniowe
       │
       ▼
WSPÓLNY MODEL DOKUMENTU
       │
       ▼
┌─────────────┐
│   FILTER    │
└──────┬──────┘
       │
       ▼
FORMAT NATYWNY
```

Kluczowym celem projektu nie jest więc mechaniczne przepisanie klas Java na Python.

Celem jest:

> **odtworzenie kontraktu i zachowania filtrów Okapi w niezależnym od JVM środowisku Python oraz zautomatyzowanie procesu importowania kolejnych filtrów.**

---

# 3. Najważniejsza hipoteza B+R

Hipoteza projektu brzmi:

> Jeżeli wspólny model dokumentowy i podstawowe kontrakty filtrów Okapi zostaną odtworzone w Pythonie, a z istniejących implementacji Java będzie można automatycznie wydobywać metadane, strukturę reguł i istotne wzorce działania, to znaczną część procesu migracji nowych filtrów można zautomatyzować.

Nie zakładamy, że każdy filtr będzie można przekonwertować automatycznie w 100%.

Projekt ma zamiast tego określić:

1. co można wyciągnąć automatycznie,
2. co można wygenerować,
3. co wymaga adaptera,
4. co wymaga ręcznej implementacji,
5. czego nie da się bezpiecznie odwzorować automatycznie,
6. jak zmierzyć zgodność implementacji Python z implementacją referencyjną Okapi.

---

# 4. Kluczowa zmiana względem wcześniejszego podejścia

Nie budujemy:

```text
Markdown.java
      ↓
Markdown.py
```

jako ręcznej translacji kodu.

Budujemy:

```text
Okapi JAR
   ↓
Analyzer
   ↓
Filter IR
   ↓
Generator / Adapter
   ↓
Python Filter
```

To jest zasadnicza różnica.

---

# 5. Filter IR — centralny element projektu

Najważniejszym artefaktem projektu ma być **Filter Intermediate Representation (Filter IR)**.

IR jest neutralnym opisem zachowania filtra.

Przykładowo:

```yaml
filter:
  name: markdown
  extensions:
    - md
    - markdown
  mime_types:
    - text/markdown

rules:

  heading:
    classification: translatable
    extraction: text

  paragraph:
    classification: translatable
    extraction: text

  inline_code:
    classification: protected
    extraction: inline

  fenced_code:
    classification: protected
    extraction: block

  image_alt:
    classification: translatable
    extraction: attribute

  link_target:
    classification: protected
    extraction: mixed

  metadata:
    classification: configurable
    extraction: metadata
```

To jest przykład koncepcyjny, a nie ustalony jeszcze format końcowy.

IR powinien być:

- jednoznaczny,
- walidowalny,
- wersjonowany,
- niezależny od Javy,
- niezależny od konkretnego generatora,
- możliwy do ręcznej korekty,
- możliwy do testowania,
- możliwy do porównywania między wersjami.

---

# 6. Architektura nowego projektu

Proponowana struktura:

```text
okapi-python/
│
├── README.md
├── LICENSE
├── pyproject.toml
│
├── docs/
│   ├── KONCEPCJA.md
│   ├── ARCHITEKTURA.md
│   ├── FILTER_IR.md
│   ├── IMPORTER.md
│   ├── DIFFERENTIAL_TESTING.md
│   ├── ZGODNOSC_OKAPI.md
│   └── PLAN_ROZWOJU.md
│
├── analyzer/
│   ├── jar_inspector/
│   ├── class_inspector/
│   ├── bytecode/
│   ├── metadata/
│   ├── dependencies/
│   └── rule_extractor/
│
├── filter_ir/
│   ├── schema/
│   ├── model/
│   ├── parser/
│   ├── validator/
│   └── normalizer/
│
├── core/
│   ├── events/
│   ├── document/
│   ├── text_unit/
│   ├── text_fragment/
│   ├── inline_code/
│   ├── skeleton/
│   ├── parameters/
│   ├── reader/
│   └── writer/
│
├── importer/
│   ├── discovery/
│   ├── extraction/
│   ├── ir_generation/
│   ├── python_generation/
│   └── validation/
│
├── differential/
│   ├── java_oracle/
│   ├── python_runner/
│   ├── event_normalizer/
│   ├── comparator/
│   └── reports/
│
├── filters/
│   ├── markdown/
│   ├── html/
│   ├── xml/
│   ├── yaml/
│   └── ...
│
├── fixtures/
│   ├── markdown/
│   ├── html/
│   └── ...
│
├── tests/
│   ├── core/
│   ├── ir/
│   ├── analyzer/
│   ├── importer/
│   ├── differential/
│   └── filters/
│
├── research/
│   ├── okapi/
│   ├── bytecode/
│   ├── parsers/
│   └── reports/
│
└── tools/
    ├── inspect_filter.py
    ├── import_filter.py
    ├── compare_filter.py
    └── build_filter.py
```

Nazwa repozytorium jest robocza. Przed utworzeniem publicznego repozytorium należy ustalić finalną nazwę projektu.

---

# 7. Python Filter Core

Drugim filarem projektu jest niezależny od konkretnego formatu **Python Filter Core**.

Core ma zastąpić tę część infrastruktury Okapi, która obecnie wymaga JVM.

Nie chodzi o odtworzenie całego Okapi Framework.

Zakres powinien zostać ograniczony do tego, co jest niezbędne do:

- odczytu dokumentu,
- ekstrakcji treści,
- reprezentacji jednostek tłumaczeniowych,
- reprezentacji inline codes,
- reprezentacji protected content,
- zachowania skeleton,
- generowania zdarzeń,
- zapisu dokumentu,
- obsługi parametrów filtrów,
- obsługi błędów,
- testowania round-trip.

---

# 8. Model dokumentu

Docelowy przepływ powinien operować na strukturach semantycznych, a nie na sztucznie wstawianych markerach tekstowych.

Koncepcyjnie:

```text
Document
 │
 ├── StartDocument
 │
 ├── TextUnit
 │    ├── TextFragment
 │    ├── InlineCode
 │    ├── InlineCode
 │    └── TextFragment
 │
 ├── DocumentPart
 │
 └── EndDocument
```

Szczegółowy model będzie przedmiotem pierwszego etapu B+R.

To ma szczególne znaczenie dla problemu obserwowanego obecnie w „Tłumaczu”, gdzie inline codes są tymczasowo maskowane markerami tekstowymi.

Docelowy Python Core powinien przechowywać inline code jako **strukturę modelu dokumentu**, a nie jako fragment zwykłego tekstu.

---

# 9. Dlaczego nie chcemy markerów tekstowych

Obecny model typu:

```text
tekst __OKAPI_CODE_0__ tekst
```

jest podatny na błędy, ponieważ backend tłumaczeniowy może potraktować marker jako normalny tekst.

Model strukturalny:

```text
TextFragment("tekst ")
Code(...)
TextFragment(" tekst")
```

eliminuje tę klasę problemów na poziomie modelu.

Nie oznacza to automatycznie, że wszystkie problemy obecnego „Tłumacza” znikną. Jest to jednak ważna przesłanka architektoniczna dla nowego Core.

---

# 10. Analyzer JAR

Pierwszym narzędziem użytkowym projektu powinien być:

```text
okapi-filter-inspect <filter.jar>
```

Narzędzie nie konwertuje jeszcze filtra.

Najpierw odpowiada:

### Identyfikacja

- nazwa filtra,
- wersja,
- producent,
- licencja,
- MIME types,
- rozszerzenia,
- klasy główne.

### Zależności

- biblioteki,
- inne moduły Okapi,
- wymagane klasy,
- zasoby.

### Parametry

- nazwy parametrów,
- wartości domyślne,
- typy,
- zależności,
- ustawienia wpływające na ekstrakcję.

### Struktura

- klasy,
- interfejsy,
- dziedziczenie,
- wywołania kluczowych API,
- parsery,
- writer,
- eventy.

### Reguły

Próba identyfikacji:

- elementów tłumaczalnych,
- elementów chronionych,
- inline codes,
- bloków chronionych,
- atrybutów tłumaczalnych,
- atrybutów chronionych,
- skeleton,
- reguł zapisu,
- subfiltrów.

Wynikiem powinien być raport:

```text
ANALIZA FILTRA

Filter: Markdown
Coverage estimate: 78%

Metadata ................. 100%
Parameters ............... 100%
MIME/extensions .......... 100%
Event model ............... 95%
Inline rules .............. 82%
Block rules ............... 76%
Writer rules .............. 71%
Dynamic logic ............. 42%

Automatic extraction: AVAILABLE
Manual review: REQUIRED
```

Wartość procentowa jest przykładowa. Mechanizm wyliczania pokrycia trzeba dopiero zdefiniować.

---

# 11. Bytecode analysis

Analizator może wykorzystywać kilka poziomów informacji.

## Poziom 1 — zawartość JAR

- manifest,
- resources,
- properties,
- XML,
- JSON,
- META-INF,
- nazwy klas.

## Poziom 2 — struktura klas

- klasy,
- metody,
- pola,
- interfejsy,
- dziedziczenie,
- sygnatury.

## Poziom 3 — bytecode

- instrukcje,
- wywołania metod,
- warunki,
- pętle,
- operacje na stringach,
- używane stałe,
- przepływ sterowania.

## Poziom 4 — analiza semantyczna

Wykrywanie wzorców:

```text
if tag == ...
    → rule

createTextUnit(...)
    → translatable content

addCode(...)
    → inline code

writeSkeleton(...)
    → skeleton

setSource(...)
    → source representation
```

Nie wolno zakładać, że takie mapowanie będzie zawsze możliwe.

Dlatego wynik analizatora powinien zawierać również poziom pewności:

```text
RULE:
  type = protected_inline
  source = bytecode
  confidence = high
```

albo:

```text
RULE:
  type = mixed_content
  source = inferred
  confidence = medium
  manual_review = true
```

---

# 12. Importer

Docelowo użytkownik powinien móc wykonać:

```bash
okapi-python import-filter path/to/filter.jar
```

Proces:

```text
1. Odczytaj JAR
       ↓
2. Zidentyfikuj filtr
       ↓
3. Zidentyfikuj zależności
       ↓
4. Przeanalizuj strukturę
       ↓
5. Przeanalizuj bytecode
       ↓
6. Wyodrębnij reguły
       ↓
7. Utwórz Filter IR
       ↓
8. Zweryfikuj IR
       ↓
9. Wygeneruj szkielet Python
       ↓
10. Wygeneruj testy
       ↓
11. Uruchom differential testing
       ↓
12. Raportuj różnice
       ↓
13. Iteracyjnie uzupełnij implementację
       ↓
14. Zbuduj pakiet filtra
```

---

# 13. Automatyzacja musi być warstwowa

Nie projektujemy systemu:

```text
JAR → magicznie działający Python
```

Projektujemy:

```text
JAR
 ↓
ANALIZA
 ↓
IR
 ↓
GENEROWANIE
 ↓
TEST
 ↓
RAPORT
 ↓
KOREKTA
 ↓
TEST
 ↓
PAKIET
```

Dzięki temu system może być użyteczny nawet wtedy, gdy automatyczna konwersja osiąga np. 60–80%.

To nadal może znacząco skrócić pracę człowieka.

---

# 14. Differential testing

To jeden z najważniejszych elementów całego projektu.

Implementacja Java Okapi będzie traktowana jako **oracle referencyjny** na etapie migracji.

Ten sam dokument:

```text
             dokument
                │
        ┌───────┴───────┐
        ▼               ▼
    Java Okapi       Python Core
        │               │
        ▼               ▼
     events           events
        │               │
        └───────┬───────┘
                ▼
          normalizacja
                │
                ▼
             DIFF
```

Porównywane mogą być m.in.:

- liczba eventów,
- typy eventów,
- TextUnit,
- source,
- target,
- inline codes,
- protected content,
- skeleton,
- metadata,
- kolejność,
- finalny output.

---

# 15. Round-trip testing

Drugi poziom testowania:

```text
input
  ↓
Java filter
  ↓
events
  ↓
Java writer
  ↓
output-java
```

oraz:

```text
input
  ↓
Python filter
  ↓
events
  ↓
Python writer
  ↓
output-python
```

Następnie:

```text
output-java
     ↕
output-python
```

Porównanie musi uwzględniać różnice formalne, które nie zmieniają semantyki dokumentu.

Nie wolno zakładać, że zwykłe porównanie bajtowe będzie właściwym kryterium dla każdego formatu.

---

# 16. Trzy poziomy zgodności

Projekt powinien rozróżniać:

## Poziom A — zgodność ekstrakcji

Python rozpoznaje te same elementy, które Java uznaje za tłumaczalne.

## Poziom B — zgodność modelu

Python tworzy równoważny model:

- TextUnit,
- TextFragment,
- Code,
- Skeleton,
- Events.

## Poziom C — zgodność round-trip

Po ponownym zapisaniu dokument jest semantycznie równoważny z dokumentem obsłużonym przez Java/Okapi.

Dopiero osiągnięcie odpowiedniego poziomu pozwala oznaczyć filtr jako gotowy.

---

# 17. Klasy filtrów

Podczas badań filtry należy podzielić według trudności.

### Klasa 1 — proste

Formaty o wyraźnej strukturze i prostych regułach.

### Klasa 2 — strukturalne

HTML/XML/YAML/JSON itp., gdzie występują elementy, atrybuty i struktura drzewa.

### Klasa 3 — mieszane

Formaty posiadające treść, kod, inline content i reguły zależne od kontekstu.

### Klasa 4 — złożone

Filtry:

- stanowe,
- wykorzystujące subfiltry,
- posiadające skomplikowany parser,
- posiadające dynamiczne reguły,
- zależne od wielu komponentów Okapi.

Najpierw należy osiągnąć automatyczny import dla klas 1–2.

---

# 18. Strategia pierwszego prototypu

Nie należy rozpoczynać od wszystkich dziewięciu filtrów istniejących obecnie w „Tłumaczu”.

Pierwszym celem powinien być jeden filtr referencyjny.

Rekomendowany:

```text
Markdown
```

Powód:

- jest już częściowo rozpoznany w dotychczasowych pracach,
- ma zarówno proste, jak i bardziej złożone reguły,
- pozwala sprawdzić inline code,
- pozwala sprawdzić fenced code,
- pozwala sprawdzić linki,
- pozwala sprawdzić obrazki,
- pozwala sprawdzić metadata,
- nadaje się do differential testing.

---

# 19. Eksperyment 1

### Cel

Sprawdzić, ile informacji o filtrze Markdown można automatycznie odzyskać z JAR.

### Wejście

```text
okapi markdown filter JAR
```

### Wynik oczekiwany

```text
metadata.json
filter-ir.yaml
analysis-report.md
generated/
tests/
```

### Pytanie badawcze

Czy analyzer potrafi automatycznie odtworzyć wystarczającą część reguł filtra, aby wygenerować użyteczny szkielet Python?

---

# 20. Eksperyment 2

Porównać ręcznie opisany IR z IR wygenerowanym automatycznie.

```text
manual IR
    ↕
generated IR
```

Pozwoli to ustalić:

- które reguły są wykrywalne,
- które są niewykrywalne,
- gdzie potrzebne są heurystyki,
- gdzie potrzebne są adaptery.

---

# 21. Eksperyment 3

Generator:

```text
Filter IR
   ↓
Python filter skeleton
```

Nie musi od razu generować pełnego filtra.

Pierwszym celem jest:

```text
class MarkdownFilter:
    metadata()
    parameters()
    parse()
    events()
    write()
```

z testami wskazującymi miejsca wymagające implementacji.

---

# 22. Eksperyment 4 — oracle

Uruchomić ten sam zestaw dokumentów przez:

```text
Java Okapi
Python Filter
```

i zbudować automatyczny raport:

```text
DOCUMENT: example.md

Events:
  Java:   14
  Python: 14

TextUnits:
  Java:   5
  Python: 5

Inline codes:
  Java:   3
  Python: 3

Differences:
  0

Round-trip:
  PASS
```

---

# 23. Co oznacza „eliminacja Javy”

W projekcie trzeba bardzo precyzyjnie zdefiniować ten cel.

### Nie oznacza:

> „nigdy nie uruchamiamy Javy podczas developmentu”.

### Oznacza:

> **produkcyjny Python Filter Core oraz produkcyjne filtry nie wymagają JVM do działania.**

JVM może przez pewien czas pełnić rolę:

- referencji,
- oracle,
- narzędzia walidacyjnego,
- źródła informacji dla importera,
- środowiska porównawczego.

Docelowo użytkownik „Tłumacza” nie powinien potrzebować JRE/JDK tylko po to, aby obsłużyć format dokumentu.

---

# 24. Licencjonowanie

Okapi Framework jest projektem open source i jego oficjalna strona wskazuje na wykorzystanie otwartych standardów oraz interoperacyjność.

Przed dystrybucją wygenerowanych filtrów należy jednak przeprowadzić osobną analizę licencyjną:

- licencja konkretnego filtra,
- licencje zależności,
- zakres praw do reimplementacji,
- NOTICE,
- attribution,
- sposób dystrybucji metadanych,
- ewentualne ograniczenia dotyczące redystrybucji.

Nie należy automatycznie zakładać, że fakt użycia informacji z JAR daje prawo do redystrybucji dowolnego wygenerowanego kodu.

Powstanie osobny dokument:

```text
docs/LICENSING.md
```

---

# 25. Zasada „nie kopiujemy implementacji”

Projekt powinien preferować:

```text
ANALIZA ZACHOWANIA
        ↓
MODEL
        ↓
REIMPLEMENTACJA
```

a nie:

```text
DEKOMPILACJA
        ↓
KOPIA KODU
        ↓
MECHANICZNE TŁUMACZENIE JAVA → PYTHON
```

To ważne zarówno technicznie, jak i prawnie.

Analyzer ma ustalić **co filtr robi**, a nie być narzędziem do bezrefleksyjnego kopiowania kodu Java.

---

# 26. API importera

Docelowe CLI:

```bash
okapi-python inspect filter.jar
okapi-python analyze filter.jar
okapi-python extract filter.jar
okapi-python generate filter.jar
okapi-python test filter-name
okapi-python compare filter-name
okapi-python build filter-name
okapi-python import filter.jar
```

Docelowo można uprościć workflow do:

```bash
okapi-python import filter.jar
```

i otrzymać:

```text
analysis/
generated/
tests/
reports/
dist/
```

---

# 27. Pakiet filtra

Po uzyskaniu stabilnego filtra Python powinien powstać niezależny pakiet:

```text
filter-markdown/
    manifest.json
    filter.py
    parameters.json
    tests/
    README.md
```

W przyszłości może zostać opakowany w format zgodny z systemem pluginów „Tłumacza”, ale **nie powinno to być zależnością projektu B+R**.

To zapewni separację:

```text
Okapi Python
    ↓
uniwersalne filtry
    ↓
adapter Tłumacz
```

---

# 28. Relacja z projektem „Tłumacz”

Projekt „Tłumacz” nie powinien być miejscem eksperymentów z parserami i bytecode.

Integracja powinna nastąpić dopiero po osiągnięciu stabilnego kontraktu.

Proponowany model:

```text
OKAPI-PYTHON
    │
    ├── Core
    ├── Analyzer
    ├── IR
    ├── Importer
    ├── Differential Tester
    └── Filters
          │
          ▼
       RELEASE
          │
          ▼
      TŁUMACZ V4
```

„Tłumacz” powinien znać jedynie stabilne API.

---

# 29. Kryteria sukcesu projektu

Projekt uznajemy za technologicznie udany, gdy:

1. istnieje niezależny Python Filter Core,
2. nie wymaga JVM podczas produkcyjnego przetwarzania,
3. istnieje formalny Filter IR,
4. istnieje analyzer JAR,
5. istnieje importer,
6. istnieje generator szkieletów Python,
7. istnieje differential testing,
8. istnieje round-trip testing,
9. istnieje raport pokrycia automatycznej ekstrakcji,
10. co najmniej jeden filtr jest odtworzony bez Javy,
11. proces dodania kolejnego filtra jest znacząco prostszy niż ręczny port,
12. wynik można zapakować niezależnie od „Tłumacza”.

---

# 30. Kryteria „filtr gotowy”

Filtr nie może być uznany za gotowy tylko dlatego, że:

```text
Python uruchamia parser.
```

Musi przejść:

```text
[ ] metadata
[ ] parameters
[ ] extraction
[ ] TextUnits
[ ] inline codes
[ ] protected content
[ ] skeleton
[ ] writer
[ ] round-trip
[ ] differential comparison
[ ] edge cases
[ ] błędne wejście
[ ] duże dokumenty
[ ] Unicode
[ ] dokumentacja
[ ] pakiet dystrybucyjny
```

---

# 31. TDD jako obowiązkowa metoda rozwoju

Każdy nowy element implementacji ma powstawać według:

```text
RED
 ↓
test failing
 ↓
GREEN
 ↓
minimal implementation
 ↓
REFACTOR
 ↓
verification
```

Dotyczy to szczególnie:

- parserów,
- IR,
- analyzerów,
- eventów,
- generatorów,
- comparatorów,
- writerów.

Nie wolno tworzyć produkcyjnego kodu tylko dlatego, że „wiemy jak powinien działać”.

Test ma najpierw wykazać brak wymaganej funkcji.

---

# 32. Dokumentacja

Dokumentacja projektu będzie traktowana jako część produktu.

Minimalny zestaw:

```text
README.md
docs/KONCEPCJA.md
docs/ARCHITEKTURA.md
docs/FILTER_IR.md
docs/IMPORTER.md
docs/ANALYZER.md
docs/DIFFERENTIAL_TESTING.md
docs/LICENSING.md
docs/ROADMAP.md
CHANGELOG.md
```

Każda istotna zmiana architektury musi aktualizować dokumentację.

---

# 33. Backupy

Przy dużych zmianach w kodzie wykonywany będzie backup przed rozpoczęciem modyfikacji.

Backup powinien zawierać:

- źródła,
- dokumentację,
- konfigurację,
- testy,
- aktualny stan projektu.

Eksperymenty mogą być wykonywane w osobnych gałęziach/worktree.

---

# 34. Separacja od „Tłumacza”

Rekomendowana organizacja:

```text
/home/frs/Projekty/
│
├── tlumacz-v4/
│
└── okapi-python/
```

Nie:

```text
tlumacz-v4/
└── filtry-python/
```

jak w obecnym eksperymencie.

Obecny katalog `filtry-python/` w „Tłumaczu” należy traktować jako **materiał badawczy / prototyp**, który po utworzeniu projektu może zostać przeniesiony lub skopiowany do nowego repozytorium.

Nie należy usuwać go automatycznie.

---

# 35. Dlaczego osobny projekt jest lepszy

### 1. Niezależny cykl rozwoju

Okapi Python może rozwijać się szybciej lub wolniej niż „Tłumacz”.

### 2. Brak sprzężenia

Błąd eksperymentalnego parsera nie powinien destabilizować aplikacji użytkowej.

### 3. Reużywalność

Projekt może być wykorzystany przez inne aplikacje lokalizacyjne.

### 4. Własne wydania

Możliwe będzie:

```text
okapi-python-core 1.x
okapi-python-markdown 1.x
okapi-python-html 1.x
```

niezależnie od wersji „Tłumacza”.

### 5. Możliwość publikacji

Projekt może zostać opublikowany jako samodzielny projekt open source.

### 6. Lepsze badania

Eksperymenty z bytecode, parserami i heurystykami nie zaśmiecają głównego repozytorium.

---

# 36. Roadmapa

## Faza 0 — Projekt

- ustalenie nazwy,
- repozytorium,
- licencja,
- struktura,
- dokumentacja,
- zasady TDD.

## Faza 1 — Core

- Event model,
- Document,
- TextUnit,
- TextFragment,
- Code,
- Skeleton,
- Parameters,
- Reader,
- Writer.

## Faza 2 — Analyzer

- JAR inspector,
- class inspector,
- metadata extractor,
- dependency scanner.

## Faza 3 — Filter IR

- schema,
- model,
- validator,
- serializer,
- versioning.

## Faza 4 — Rule extraction

- bytecode analysis,
- heurystyki,
- confidence scoring,
- raport pokrycia.

## Faza 5 — Importer

```text
JAR → IR → Python skeleton
```

## Faza 6 — Differential testing

```text
Java ↔ Python
```

## Faza 7 — pierwszy pełny filtr

Markdown.

## Faza 8 — kolejne filtry

Najpierw formaty proste, potem strukturalne i złożone.

## Faza 9 — dystrybucja

Pakiety niezależne od „Tłumacza”.

## Faza 10 — integracja

Dopiero tutaj:

```text
Tłumacz → Python Filter Core
```

---

# 37. Największe ryzyka

## Ryzyko 1 — filtr nie jest deklaratywny

Rozwiązanie:

IR + analiza bytecode + ręczne adaptery.

## Ryzyko 2 — dynamiczne zachowanie

Rozwiązanie:

oracle + differential testing.

## Ryzyko 3 — subfiltry

Rozwiązanie:

model zależności w IR.

## Ryzyko 4 — różnice parserów

Rozwiązanie:

testy semantyczne i fixture corpus.

## Ryzyko 5 — błędy round-trip

Rozwiązanie:

oddzielne testy ekstrakcji i zapisu.

## Ryzyko 6 — niepełna automatyzacja

Rozwiązanie:

system confidence + manual review.

## Ryzyko 7 — problemy licencyjne

Rozwiązanie:

osobny audyt licencyjny przed dystrybucją.

---

# 38. Najważniejszy cel praktyczny

Ostatecznym rezultatem nie ma być:

> „Mamy jeden filtr Markdown napisany w Pythonie”.

To byłby tylko dowód koncepcji.

Celem jest:

> **„Mamy mechanizm, który pozwala wziąć istniejący filtr Okapi, przeanalizować go, opisać w Filter IR, wygenerować implementację Python, uruchomić testy różnicowe względem oryginału i przygotować niezależny pakiet bez JVM.”**

To jest właściwy poziom automatyzacji.

---

# 39. Docelowy przepływ użytkownika

Po zakończeniu projektu użytkownik nie powinien znać szczegółów JVM ani implementacji Okapi.

Powinien móc wykonać:

```bash
okapi-python import path/to/new-filter.jar
```

a narzędzie powinno odpowiedzieć:

```text
[1/8] Identyfikacja filtra ............. OK
[2/8] Analiza zależności ............... OK
[3/8] Ekstrakcja metadanych ............ OK
[4/8] Ekstrakcja reguł ................ PARTIAL
[5/8] Generowanie Filter IR ............ OK
[6/8] Generowanie Python ............... OK
[7/8] Differential testing ............. REVIEW REQUIRED
[8/8] Raport ........................... GENERATED

Coverage: 87%

Automatic:
  metadata      100%
  parameters     96%
  rules          84%
  writer         81%

Manual review:
  3 rules
  1 dynamic dependency

Output:
  generated/filter_name/
  reports/filter_name/
  tests/filter_name/
```

To jest docelowy model „importowania” nowych filtrów.

---

# 40. Wniosek końcowy

Kierunek należy traktować jako osobny projekt B+R.

Najważniejszym osiągnięciem nie będzie port pojedynczego filtra, lecz opracowanie:

```text
Python Filter Core
+
Filter IR
+
Okapi Analyzer
+
Rule Extractor
+
Python Generator
+
Differential Tester
```

Razem tworzą one **pipeline migracji filtrów Okapi z ekosystemu Java do ekosystemu Python**.

„Tłumacz” powinien być dopiero jednym z odbiorców tego rozwiązania.

Takie rozdzielenie pozwala osiągnąć główny warunek projektu:

> **JVM nie jest wymagane przez docelowy runtime filtrów dokumentowych.**

Java pozostaje jedynie opcjonalnym narzędziem referencyjnym podczas fazy migracyjnej.

---

## 41. Status decyzji

**DECYZJA: ZATWIERDZONE DO ROZPOCZĘCIA B+R**

Następny etap nie powinien jeszcze polegać na masowym przepisywaniu filtrów.

Pierwszym zadaniem jest utworzenie niezależnego projektu oraz wykonanie kontrolowanego proof-of-concept:

```text
Okapi Markdown JAR
        ↓
Analyzer
        ↓
Filter IR
        ↓
Python Core
        ↓
Python Markdown Filter
        ↓
Differential Test
        ↓
Round-trip Test
```

Dopiero wynik tego eksperymentu określi, jak dużą część procesu można rzeczywiście zautomatyzować.

---

## Źródła i podstawa koncepcji

- Okapi Framework — oficjalny opis projektu i jego celu: komponenty dla lokalizacji i tłumaczenia dokumentacji oraz oprogramowania, interoperacyjność i otwarte standardy.
- Dokumentacja i materiały projektu Okapi dotyczące filtrów i wspólnego przetwarzania dokumentów.
- Analiza istniejącej architektury „Tłumacza” i wcześniejsze eksperymenty z `filtry-python/`.
- Wewnętrzne wyniki badań nad reprezentacją `TextUnit`, `TextFragment`, inline codes, skeleton oraz eventami.
- Wyniki badań nad problemem markerów `__OKAPI_CODE_N__` i koniecznością odejścia od traktowania inline codes jako zwykłego tekstu.

Źródła internetowe wykorzystane przy przygotowaniu koncepcji:
- https://www.okapiframework.org/
- repozytorium projektu Okapi Framework i jego dokumentacja.
