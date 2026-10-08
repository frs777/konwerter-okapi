# Okapi execution — current state

## Zakres audytu

Audyt wykonano dla lokalnego checkoutu repozytorium, z rozdzieleniem kodu roboczego od katalogów `backups/` i artefaktów historycznych.

## Ustalenia

### 1. Aktualny rdzeń

Istnieją dwie równoległe warstwy:

- istniejący Pythonowy rdzeń filtrów:
  - `core/filter.py`
  - `filters/`
  - `importer/`
- nowa warstwa execution:
  - `execution/contracts.py`
  - `execution/capabilities.py`
  - `execution/registry.py`
  - `execution/resolver.py`
  - `execution/job.py`
  - `execution/ports.py`
  - `execution/protocol.py`
  - `execution/service.py`

`core/filter.py` implementuje Pythonowy lifecycle inspirowany `IFilter`: `open → has_next/next → close`, z osobnym Writerem.

### 2. Filter execution

Nowa warstwa posiada:

```text
DocumentRequest
    ↓
FilterResolver
    ↓
FilterDescriptor
    ↓
backend
    ↓
FilterExecutionPort
    ↓
ExecutionResult
```

`ExecutionService` dodatkowo spina lifecycle `JobCoordinator`.

### 3. Backend

Dostępne są dwa backendy:

- `MockFilterBackend` — deterministyczny backend testowy;
- `NativeFilterBackend` — uruchamia istniejące filtry Pythonowe bez Okapi/JVM.

`NativeFilterBackend` obsługuje dwa warianty wejścia istniejących filtrów: ścieżkę pliku oraz treść tekstową, wybieraną jawnie przez `source_modes`. Obsługuje również oba spotkane kontrakty `write()`: z parametrem `target` oraz zwracające gotowy tekst/bajty.

`execution/native_catalog.py` centralizuje potwierdzone kontrakty natywnych filtrów i buduje jednocześnie `FilterRegistry` oraz `NativeFilterBackend`. Automatyczny katalog obejmuje obecnie TXT, DOCX, Markdown, HTML, JSON, YAML, EPUB, XLIFF 1.2 i XLIFF 2.x. Tryb wejścia jest jawny: tekst dla TXT/Markdown/JSON/YAML/XLIFF oraz ścieżka dla DOCX/HTML/EPUB. DOCX korzysta z adaptera łączącego istniejące `DocxReader` i `DocxWriter` z jednolitym kontraktem execution.

XLIFF 1.2 i XLIFF 2.x współdzielą `.xlf/.xliff`, dlatego resolver stosuje content-aware detection namespace XML, a jawne `format`/`filter_id` zachowują pierwszeństwo.

`build_native_execution_service()` udostępnia gotowy `ExecutionService` jako publiczną granicę pakietu `execution`; klient nie musi ręcznie składać registry/backend/resolver/coordinator.

Integracja została sprawdzona przez `ExecutionService` na Markdown, YAML, XLIFF 1.2, XLIFF 2.x i TXT oraz przez publiczną fabrykę na JSON.

Nie uruchamiamy na tym etapie JVM ani Okapi runtime.

### 4. Format filters

W repo istnieją natywne implementacje Pythonowe, m.in.:

- HTML;
- DOCX.

DOCX reader posiada rozbudowany model strukturalny obejmujący m.in. inline codes, style, hyperlinks, fields, metadata i skeleton information.

### 5. CLI / tooling

`tools/okapi_convert.py` jest narzędziem do analizy JAR → Filter IR → generowanie filtra Python.

Nie jest to GUI ani runtime execution layer.

`importer/pipeline.py` realizuje pipeline analityczno-generacyjny:

```text
JAR + metadata
    ↓
extract_filter
    ↓
Filter IR
    ↓
PythonFilterGenerator
```

### 6. GUI / LLM / JVM

W aktualnych plikach Python repozytorium nie znaleziono produkcyjnego GUI opartego o Qt/Tk ani wywołań `llama.cpp`.

Wyszukiwanie `subprocess/Popen` wskazuje obecnie przede wszystkim:

- `analyzer/java_probe/probe.py`;
- testy.

Nie znaleziono w aktualnym kodzie produkcyjnym bezpośredniego uruchamiania JVM przez execution layer.

Wniosek: mechanizm wielokrotnego uruchamiania serwera LLM, o którym mowa w wcześniejszych logach aplikacji, nie znajduje się w aktualnie analizowanym rdzeniu tego repozytorium.

## Aktualny przepływ

```text
JAR / metadata
    ↓
Importer / Filter IR / generator
    ↓
Python filter implementations
    ↓
core Filter lifecycle

oraz niezależnie:

DocumentRequest
    ↓
FilterResolver
    ↓
ExecutionService
    ↓
FilterExecutionPort
    ↓
Mock backend
```

Te dwa przepływy nie są jeszcze połączone z pełnym GUI → Translation Engine → execution flow.

## Luka architektoniczna

Najważniejszą pozostałą granicą jest integracja istniejących natywnych filtrów z `FilterExecutionPort` bez uzależniania warstwy aplikacyjnej od konkretnych klas filtrów.

Docelowo:

```text
Translation Engine
    ↓
DocumentRequest
    ↓
ExecutionService
    ↓
FilterResolver
    ↓
FilterExecutionPort
    ├── Native backend
    └── Okapi backend — później
```

## Ograniczenia

- brak instalacji Javy/Okapi na tym etapie;
- brak automatycznego uruchamiania runtime;
- brak zmian w istniejącym pipeline importer/generator bez testu;
- execution layer rozwijany niezależnie od JVM.

## Aktualizacja zachowania XLIFF — 2026-10-09

Model `TextUnit` przechowuje opcjonalne `target_fragments` niezależnie od źródłowych `fragments`. Natywny XLIFF 1.2 odczytuje `<source>` i `<target>` oddzielnie. Natywny XLIFF 2.x odczytuje wszystkie `<segment>` w obrębie `<unit>`, zachowuje `unit_id`, `segment_id` i indeks segmentu w metadanych oraz reprezentuje zagnieżdżone inline codes przez `Markup.start`/`Markup.end`; puste elementy pozostają `Markup.empty`. Oba writer'y obsługują nieprefiksowane tagi i lokalne nazwy tagów z prefiksem namespace oraz tworzą brakujący `<target>`, jeśli model dostarcza tłumaczenie.

To nadal implementacja częściowa. Writer XLIFF używa skanowania tekstowego oryginalnego XML, aby ograniczyć niezamierzone formatowanie zmian, dlatego wymaga dalszych testów dla wielu segmentów bez ID, komentarzy/CDATA, nietypowego formatowania tagów i dużych zmian długości treści. Nie deklarujemy jeszcze pełnej zgodności z Okapi.

## Evidence

Świeża pełna weryfikacja z 2026-10-09 po poprawkach modelu i XLIFF:

```text
full suite: 305 passed in 63.93s
compileall: OK
```

Ten dokument opisuje stan repozytorium, a nie docelową architekturę.
