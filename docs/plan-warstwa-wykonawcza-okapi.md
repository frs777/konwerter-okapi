# Plan implementacji warstwy wykonawczej filtrów Okapi

**Projekt:** konwerter-okapi  
**Dokument:** plan implementacyjny warstwy wykonawczej  
**Status:** plan do zatwierdzenia przed implementacją  
**Data:** 2026-10-08  
**Zakres:** TXT + DOCX jako pierwsze formaty, z architekturą umożliwiającą późniejsze filtry natywne

---

## 0. Cel projektu

Zbudować niezależną **Filter Execution Layer**, która:

1. izoluje aplikację Python/GUI od Javy i API Okapi;
2. zachowuje semantykę filtrów Okapi;
3. obsługuje konfigurację filtrów i ich lifecycle;
4. zamienia dokument na stabilny kontrakt domenowy;
5. pozwala wykonać tłumaczenie na jednostkach tekstowych;
6. odtwarza dokument przez mechanizmy Okapi;
7. obsługuje TXT i DOCX jako pierwsze przypadki;
8. pozwala w przyszłości zastępować backend Okapi implementacjami natywnymi;
9. umożliwia testowanie Okapi jako backendu referencyjnego;
10. nie wymaga Javy w procesie GUI/aplikacji głównej.

### Główna zasada

> **Okapi jest backendem wykonawczym, a nie kontraktem całej aplikacji.**

Docelowo:

```text
GUI
  ↓
Translation Engine
  ↓
Document Contract V4
  ↓
Filter Resolver
  ↓
Filter Execution Port
  ├── Native Backend
  └── Okapi Backend
        ↓
     Python–Java IPC
        ↓
     Okapi Filter Host
        ↓
     Controlled Okapi Runtime
```

---

# 1. Status ustaleń

## 1.1. Potwierdzone przez dokumentację Okapi

Okapi definiuje wspólne API `IFilter`. Filtr otwiera `RawDocument`, generuje strumień `Event`, a najważniejsze dla tłumaczenia zdarzenia zawierają `TextUnit`.

`IFilter` jest jednocześnie `Iterator<Event>` i posiada m.in.:

- `open(RawDocument)`;
- `hasNext()`;
- `next()`;
- `createFilterWriter()`;
- `setParameters(IParameters)`;
- `setFilterConfigurationMapper(...)`;
- `cancel()`;
- `close()`.

Okapi dokumentuje również `IFilterWriter`, który obsługuje eventy i odpowiada za rekonstrukcję formatu wyjściowego.

Źródła:
- https://okapiframework.org/devguide/filters.html
- https://okapiframework.org/devguide/gettingstarted.html
- https://okapiframework.org/javadoc/net/sf/okapi/common/filters/IFilter.html
- https://okapiframework.org/javadoc/net/sf/okapi/common/resource/RawDocument.html
- https://okapiframework.org/javadoc/net/sf/okapi/common/filterwriter/IFilterWriter.html

## 1.2. Potwierdzony model eventów

Minimalny cykl dokumentu:

```text
START_DOCUMENT
  ↓
[START_SUBDOCUMENT / START_GROUP / DOCUMENT_PART / TEXT_UNIT ...]
  ↓
END_DOCUMENT
```

Okapi wymienia również eventy batchowe i sterujące, m.in.:

- `START_BATCH`;
- `START_BATCH_ITEM`;
- `RAW_DOCUMENT`;
- `START_DOCUMENT`;
- `START_SUBDOCUMENT`;
- `START_GROUP`;
- `DOCUMENT_PART`;
- `TEXT_UNIT`;
- `END_GROUP`;
- `END_SUBDOCUMENT`;
- `END_DOCUMENT`;
- `CANCELED`;
- `FINISHED`;
- `NO_OP`;
- `CUSTOM`;
- `END_BATCH_ITEM`;
- `END_BATCH`.

Nie wolno zakładać, że każdy filtr generuje identyczny podzbiór eventów.

## 1.3. Potwierdzona konfiguracja

Okapi posiada identyfikatory konfiguracji filtrów. Przykładowo dokumentacja Tikal wskazuje:

```text
.docx → okf_openxml
.odt  → okf_openoffice
.po   → okf_po
```

Możliwe jest wskazanie własnej konfiguracji przez `-fc`, a konfiguracje użytkownika są przechowywane jako `.fprm`.

Źródło:
- https://gitlab.com/okapiframework/Okapi/-/blob/main/help/applications/tikal/index.html

Wniosek:

> `filter_id`, `filter_config_id` i parametry filtra muszą być pierwszorzędnymi elementami kontraktu wykonawczego.

---

# 2. Decyzje architektoniczne

## 2.1. Styl architektury

Przyjmujemy:

- modular monolith po stronie aplikacji;
- Ports & Adapters / Hexagonal Architecture;
- osobny proces dla Okapi/JVM;
- pluginowy model backendów filtrów;
- kontrakt dokumentowy niezależny od Okapi.

Nie tworzymy mikroserwisu sieciowego tylko po to, aby uruchomić filtr lokalnie.

## 2.2. Granica Javy

Java może występować wyłącznie za:

```text
FilterExecutionPort
       ↓
OkapiFilterBackend
       ↓
OkapiProcessBridge
       ↓
OkapiFilterHost
       ↓
JVM
```

Kod GUI i Translation Engine nie może importować klas Java/Okapi.

## 2.3. Stabilny kontrakt

Warstwa aplikacyjna operuje na:

```text
DocumentContract V4
```

a nie na:

```text
Okapi Event
TextUnit
RawDocument
```

Mapowanie wykonuje adapter.

---

# 3. Etap 0 — inwentaryzacja istniejącego konwertera

**Cel:** nie projektować drugiego systemu obok obecnego.

### Kroki

1. Ustalić rzeczywisty katalog repozytorium `konwerter-okapi`.
2. Zidentyfikować punkt wejścia GUI.
3. Zidentyfikować obecny moduł wyboru filtra.
4. Zidentyfikować obecny moduł tłumaczenia.
5. Zidentyfikować wszystkie miejsca uruchamiające Javę/llama/serwery pomocnicze.
6. Zidentyfikować obecny mechanizm:
   - wczytywania TXT;
   - wczytywania DOCX;
   - ekstrakcji;
   - podziału na segmenty;
   - tłumaczenia;
   - zapisu;
   - błędów;
   - anulowania.
7. Zbudować call graph dla aktualnego przepływu.
8. Zmierzyć liczbę uruchomień serwera/filtra na jeden dokument.
9. Sprawdzić, czy jeden plik powoduje wielokrotne otwieranie tego samego backendu.
10. Zidentyfikować potencjalne wywołania powodujące nadmiar requestów.

### Artefakt

`docs/architecture/okapi-execution-current-state.md`

### Kryterium zakończenia

Mamy diagram:

```text
GUI → intake → resolver → extraction → translation → writer
```

z rzeczywistymi modułami i funkcjami projektu.

---

# 4. Etap 1 — reverse engineering obecnego przepływu

Metoda:

```text
QUESTION
→ TRIAGE
→ STATIC MODEL
→ HYPOTHESIS
→ CONTROLLED RUNTIME TEST
→ CORRELATION
→ DOCUMENTATION
```

### 4.1. Static analysis

Dla każdego punktu wejścia sprawdzić:

- importy;
- wywołania;
- zależności;
- singletony;
- cache;
- subprocess;
- IPC;
- thread/process boundaries;
- obsługę wyjątków;
- cleanup.

### 4.2. Dynamic analysis

Dla TXT i DOCX wykonać kontrolowany przebieg:

```text
1 plik
1 kliknięcie tłumaczenia
1 backend
1 job
```

Rejestrować:

- timestamp;
- request/job ID;
- start backendu;
- start filtra;
- open;
- extraction;
- liczba TEXT_UNIT;
- translation calls;
- writer;
- close;
- shutdown.

### 4.3. Szczególny test

Sprawdzić hipotezę:

> „Jedno tłumaczenie powoduje wielokrotne wywołanie serwera/filtra.”

Jeżeli występuje, znaleźć dokładną funkcję powodującą każde dodatkowe wywołanie.

### Kryterium

Nie implementujemy nowej warstwy, dopóki nie mamy jednoznacznego obrazu aktualnego lifecycle.

---

# 5. Etap 2 — zbudowanie referencyjnego modelu Okapi

Tworzymy mały program referencyjny Java, który **nie jest jeszcze częścią aplikacji**.

Ma obsługiwać:

```text
input
filter configuration
source locale
target locale
parameters
→ events
→ writer
→ output
```

## 5.1. TXT

Test:

```text
TXT
→ PlainTextFilter
→ events
→ writer
→ TXT
```

## 5.2. DOCX

Test:

```text
DOCX
→ OpenXMLFilter
→ events
→ writer
→ DOCX
```

## 5.3. Rejestrowane dane

Dla każdego eventu:

```text
event_type
resource_type
unit_id
name
translatable
source
target
properties
annotations
inline codes
skeleton metadata
```

Nie zapisujemy całej binarnej zawartości dokumentu do logu.

---

# 6. Etap 3 — zdefiniowanie Document Contract V4

Kontrakt musi być niezależny od Okapi.

Minimalny model:

```text
Document
├── id
├── format
├── source_locale
├── target_locales
├── metadata
├── units[]
│   ├── id
│   ├── name
│   ├── source
│   ├── target
│   ├── translatable
│   ├── inline_codes
│   ├── properties
│   ├── annotations
│   └── backend_metadata
└── reconstruction
```

### Ważne

`backend_metadata` może istnieć, ale nie może zdominować modelu.

Nie wolno zrobić:

```text
Document = TextUnit + pola Okapi
```

Kontrakt musi być domenowy.

---

# 7. Etap 4 — Filter Execution Port

Definiujemy interfejs:

```python
class FilterExecutionPort:
    def capabilities(self): ...
    def probe(self, request): ...
    def open(self, request): ...
    def extract(self): ...
    def apply(self, request): ...
    def validate(self, request): ...
    def merge(self, request): ...
    def cancel(self, request): ...
    def close(self, request): ...
```

To jest interfejs aplikacji, nie interfejs Okapi.

---

# 8. Etap 5 — FilterCapabilities

Każdy backend musi deklarować:

```text
backend_id
backend_version

formats[]
extensions[]
mime_types[]

input_modes[]
output_modes[]

supports_parameters
supports_custom_configuration
supports_multilingual
supports_inline_codes
supports_annotations
supports_skeleton
supports_streaming
supports_cancel

configuration_schema
```

Przykład:

```json
{
  "backend_id": "okapi",
  "filter_id": "openxml",
  "filter_config_id": "okf_openxml",
  "formats": ["docx", "xlsx", "pptx"],
  "supports_skeleton": true,
  "supports_inline_codes": true
}
```

---

# 9. Etap 6 — Filter Registry

Registry przechowuje deklaracje, nie uruchamia filtrów.

```text
FilterRegistry
├── native.txt
├── okapi.plaintext
├── okapi.openxml
└── future.native.openxml
```

Każdy wpis:

```text
id
backend
format
extensions
mime
priority
configuration
capabilities
```

---

# 10. Etap 7 — Filter Resolver

Resolver:

```text
document
  ↓
extension
  ↓
MIME
  ↓
signature/probe
  ↓
registry
  ↓
candidate filters
  ↓
priority/capabilities
  ↓
FilterDescriptor
```

Resolver nie wykonuje tłumaczenia.

### Przykład

```text
.docx
  ↓
OpenXML
  ├── native backend
  └── Okapi backend
```

W pierwszej fazie wybieramy Okapi jako backend referencyjny.

---

# 11. Etap 8 — Okapi Event Mapper

Tworzymy:

```text
OkapiEventMapper
```

Mapowanie:

```text
START_DOCUMENT
        ↓
DocumentMetadata

TEXT_UNIT
        ↓
TranslationUnit

DOCUMENT_PART
        ↓
ReconstructionPart

START_GROUP
END_GROUP
        ↓
Structure

START_SUBDOCUMENT
END_SUBDOCUMENT
        ↓
SubdocumentStructure
```

Eventy nieznane muszą być jawnie obsługiwane:

```text
SUPPORTED
IGNORED_WITH_REASON
PRESERVED
UNSUPPORTED_ERROR
```

Nie wolno po cichu wyrzucać eventu.

---

# 12. Etap 9 — inline codes

To osobny etap.

Trzeba odwzorować:

```text
TextFragment
coded text
inline codes
```

na model aplikacji.

Testy muszą obejmować:

- opening code;
- closing code;
- isolated code;
- nested codes;
- code properties;
- code order;
- code movement;
- Unicode;
- escaped content.

To jest krytyczne dla DOCX.

---

# 13. Etap 10 — skeleton/reconstruction

Najważniejsza reguła:

> Nie rekonstruujemy DOCX z samego tekstu.

Okapi dokumentuje, że do odtworzenia dokumentu potrzebne są także zasoby strukturalne/skeleton przekazywane przez eventy.

Dlatego:

```text
TranslationUnit
```

nie może być jedynym nośnikiem informacji.

Musimy zachować:

```text
document structure
non-translatable parts
skeleton/reconstruction metadata
inline codes
ordering
```

---

# 14. Etap 11 — Java Host

Tworzymy osobny proces:

```text
okapi-filter-host
```

Odpowiada za:

1. start JVM;
2. załadowanie runtime;
3. handshake;
4. rejestrację filtrów;
5. wykonanie joba;
6. event streaming;
7. writer;
8. cancel;
9. cleanup;
10. raportowanie błędów.

Nie zawiera GUI.

Nie zawiera logiki tłumaczenia.

Nie wybiera modelu LLM.

---

# 15. Etap 12 — IPC

Pierwsza wersja:

```text
JSONL over stdin/stdout
```

Każda wiadomość posiada:

```text
protocol_version
request_id
message_type
payload
```

Przykłady:

```json
{
  "protocol_version": 1,
  "request_id": "job-123",
  "message_type": "open"
}
```

Event:

```json
{
  "protocol_version": 1,
  "request_id": "job-123",
  "message_type": "text_unit",
  "unit": {...}
}
```

Zakończenie:

```json
{
  "protocol_version": 1,
  "request_id": "job-123",
  "message_type": "completed"
}
```

Błąd:

```json
{
  "protocol_version": 1,
  "request_id": "job-123",
  "message_type": "error",
  "code": "RECONSTRUCTION_FAILED"
}
```

---

# 16. Etap 13 — lifecycle jednego joba

Docelowy lifecycle:

```text
CREATED
  ↓
RESOLVING
  ↓
PROBING
  ↓
OPENING
  ↓
EXTRACTING
  ↓
EXTRACTED
  ↓
TRANSLATING
  ↓
APPLYING
  ↓
RECONSTRUCTING
  ↓
VALIDATING
  ↓
COMPLETED
```

Alternatywne zakończenia:

```text
CANCELED
FAILED
TIMEOUT
EXECUTOR_CRASHED
INVALID_INPUT
UNSUPPORTED
RECONSTRUCTION_FAILED
```

---

# 17. Etap 14 — cancellation

Cancellation musi być propagowane:

```text
GUI
 ↓
Translation Engine
 ↓
FilterExecutionPort.cancel()
 ↓
Bridge
 ↓
Okapi Host
 ↓
IFilter.cancel()
```

Po cancellation:

```text
no new translation requests
no new output commit
cleanup
job = CANCELED
```

---

# 18. Etap 15 — timeout i crash recovery

Host musi wykrywać:

```text
process exit
broken pipe
EOF
timeout
memory failure
Java exception
```

Aplikacja otrzymuje:

```text
EXECUTOR_CRASHED
```

Nie:

```text
generic exception
```

Każdy job musi mieć własny ID.

---

# 19. Etap 16 — workspace joba

Dla większych dokumentów nie przesyłamy całego DOCX jako Base64 przez JSONL.

Proponowany workspace:

```text
job/
├── input/
├── work/
├── output/
├── metadata.json
└── result.json
```

IPC przekazuje identyfikator joba i kontrolowane ścieżki.

To ogranicza zużycie pamięci i pozwala bezpiecznie obsługiwać pliki binarne.

---

# 20. Etap 17 — TXT jako pierwszy vertical slice

Implementacja:

```text
GUI
→ resolver
→ Okapi backend
→ bridge
→ host
→ PlainTextFilter
→ event mapper
→ translation
→ writer
→ TXT
```

### Definition of Done

- jeden start hosta;
- jeden job;
- poprawna liczba TEXT_UNIT;
- tłumaczenie;
- poprawny output;
- cleanup;
- brak wycieków procesu;
- cancellation działa;
- ponowne tłumaczenie nie tworzy niekontrolowanych procesów.

---

# 21. Etap 18 — DOCX jako drugi vertical slice

Implementacja:

```text
DOCX
→ okf_openxml
→ event mapper
→ translation
→ OpenXML writer
→ DOCX
```

Corpus testowy powinien obejmować:

- zwykły akapit;
- nagłówki;
- listy;
- tabele;
- linki;
- pogrubienie;
- kursywę;
- inline formatting;
- obrazy z podpisami;
- tekst nietłumaczalny;
- puste elementy;
- Unicode;
- kilka języków;
- dokument wielostronicowy;
- tekst z ręcznymi podziałami linii.

---

# 22. Etap 19 — round-trip testing

Dla każdego pliku:

```text
source
 ↓
extract
 ↓
contract
 ↓
identity translation
 ↓
merge
 ↓
output
```

Następnie:

```text
source vs output
```

Nie porównujemy tylko bajtów, ponieważ writer może legalnie zmienić nieistotne szczegóły serializacji.

Porównujemy:

- semantykę tekstu;
- strukturę;
- inline codes;
- liczby jednostek;
- kolejność;
- właściwości;
- metadata;
- możliwość ponownego otwarcia outputu.

---

# 23. Etap 20 — differential testing

Dla backendu Okapi i przyszłego native:

```text
same input
     ↓
 ┌───┴────┐
 │        │
Okapi    Native
 │        │
 └───┬────┘
     ↓
Contract V4
     ↓
semantic diff
```

To jest podstawa przyszłej migracji z Javy.

---

# 24. Etap 21 — testy błędów

Obowiązkowe przypadki:

### Input

- brak pliku;
- pusty plik;
- uszkodzony DOCX;
- nieznany format;
- zły encoding.

### Filter

- nieznany filter ID;
- nieznany configuration ID;
- błędne parametry;
- brak konfiguracji.

### Runtime

- brak JVM;
- brak JAR;
- crash JVM;
- timeout;
- broken pipe.

### Translation

- błąd modelu;
- timeout modelu;
- anulowanie;
- częściowo przetłumaczony dokument.

### Writer

- błąd rekonstrukcji;
- brak skeleton;
- niezgodny inline code;
- niepoprawny target.

---

# 25. Etap 22 — observability

Każdy job:

```text
job_id
document_id
backend_id
filter_id
filter_config_id
input_format
input_size
start_time
end_time
units_extracted
units_translated
units_failed
writer_status
runtime_pid
```

Logi muszą pozwolić odpowiedzieć:

> Dlaczego jedno kliknięcie spowodowało N uruchomień?

To jest szczególnie ważne w kontekście obecnego problemu z wielokrotnymi wywołaniami serwera.

---

# 26. Etap 23 — ochrona przed wielokrotnym uruchamianiem

Dodajemy:

```text
JobCoordinator
```

Reguła:

```text
document_id + operation_id
```

ma jeden aktywny job.

Nie wolno:

```text
click
→ start
click
→ start
callback
→ start
```

bez jawnej decyzji.

---

# 27. Etap 24 — runtime Okapi

Runtime musi być wersjonowany.

Manifest:

```json
{
  "runtime_version": "...",
  "okapi_version": "...",
  "java_version": "...",
  "artifacts": [
    {
      "name": "...",
      "sha256": "..."
    }
  ]
}
```

Nie zakładamy przypadkowej instalacji systemowej.

Nie instalujemy niczego automatycznie bez zgody użytkownika.

---

# 28. Etap 25 — bezpieczeństwo

Granica JVM powinna mieć:

- ograniczony workspace;
- brak dostępu do przypadkowych plików użytkownika;
- brak sieci, jeśli nie jest wymagana;
- limity czasu;
- kontrolę rozmiaru input/output;
- kontrolę ścieżek;
- bezpieczne cleanup;
- jawne logowanie.

Nie używamy `shell=True` do przekazywania danych użytkownika.

---

# 29. Etap 26 — test kontraktu IPC

Testy:

```text
valid request
invalid request
unknown operation
unknown protocol version
malformed JSON
missing request_id
duplicate request_id
out-of-order event
unexpected event
executor crash
EOF
timeout
cancel
```

---

# 30. Etap 27 — contract tests backendów

Każdy backend musi przejść ten sam zestaw:

```text
CapabilityContract
ExtractionContract
TranslationContract
ReconstructionContract
CancellationContract
ErrorContract
LifecycleContract
```

W przyszłości:

```text
OkapiBackend
NativeTxtBackend
NativeDocxBackend
```

będą testowane identycznym harness.

---

# 31. Etap 28 — native TXT

Dopiero po działającym Okapi backendzie tworzymy:

```text
NativeTextBackend
```

Cel:

```text
Native TXT
≈
Okapi TXT
```

na poziomie `DocumentContract V4`.

To będzie pierwszy dowód, że architektura rzeczywiście oddzieliła format od Okapi.

---

# 32. Etap 29 — native DOCX

Nie implementować od razu pełnego odpowiednika Okapi.

Najpierw:

1. zebrać corpus;
2. wyciągnąć kontrakt Okapi;
3. sklasyfikować elementy DOCX;
4. określić minimalny zakres;
5. implementować parser;
6. uruchomić differential tests;
7. rozszerzać coverage.

---

# 33. Etap 30 — migracja

Docelowa macierz:

| Format | Okapi | Native | Status |
|---|---:|---:|---|
| TXT | ✓ | ✓ | pierwszy |
| DOCX | ✓ | później | drugi |
| XLSX | ✓ | później | przyszłość |
| PPTX | ✓ | później | przyszłość |
| Markdown | ✓ | później | przyszłość |
| HTML | ✓ | później | przyszłość |

Okapi pozostaje backendem referencyjnym tak długo, jak długo native backend nie przejdzie testów zgodności.

---

# 34. Etap 31 — IcePanel

Istniejący model powinien zostać uporządkowany do:

```text
Translation Engine
        ↓
Document Contract V4
        ↓
Filter Resolver
        ↓
Filter Execution Port
        ├── Native Filter Backend
        └── Okapi Filter Backend
                  ↓
             Python–Java Bridge
                  ↓
             Okapi Filter Host
                  ↓
             Controlled Runtime
```

Dodajemy osobne flow:

### Flow A — TXT extraction

```text
GUI → Resolver → Okapi → TEXT_UNIT → Contract
```

### Flow B — TXT reconstruction

```text
Contract → Event Mapper → Writer → TXT
```

### Flow C — DOCX extraction

```text
DOCX → OpenXML → Event Stream → Contract
```

### Flow D — DOCX reconstruction

```text
Contract → Events → OpenXML Writer → DOCX
```

### Flow E — cancellation

```text
GUI → Coordinator → Bridge → Host → IFilter.cancel()
```

### Flow F — crash

```text
Host crash → Bridge → Coordinator → FAILED/CRASHED
```

---

# 35. Etap 32 — dokumentacja

Powstaną:

```text
docs/
├── architecture/
│   ├── okapi-execution-current-state.md
│   ├── okapi-execution-architecture.md
│   ├── filter-execution-contract.md
│   ├── document-contract-v4.md
│   ├── okapi-ipc-protocol.md
│   └── okapi-runtime.md
│
├── filters/
│   ├── txt.md
│   ├── docx.md
│   └── okapi-event-mapping.md
│
└── testing/
    ├── okapi-contract-tests.md
    ├── roundtrip-tests.md
    └── differential-tests.md
```

---

# 36. Etap 33 — implementacja kolejnością TDD

Każda zmiana zachowania:

```text
RED
 ↓
test fails
 ↓
GREEN
 ↓
minimal implementation
 ↓
REFACTOR
 ↓
verification
```

Nie zaczynamy od implementacji całego bridge'a.

Kolejność:

1. `DocumentContract`;
2. `FilterExecutionPort`;
3. `FilterCapabilities`;
4. `FilterRegistry`;
5. `FilterResolver`;
6. `Job`;
7. IPC schema;
8. mock executor;
9. Okapi Host;
10. Okapi backend;
11. TXT;
12. DOCX;
13. cancellation;
14. crash handling;
15. native TXT;
16. differential testing.

---

# 37. Etap 34 — mock backend przed Javą

Przed uruchomieniem rzeczywistego Okapi tworzymy:

```text
MockFilterBackend
```

Pozwala testować:

- lifecycle;
- resolver;
- job coordinator;
- IPC;
- errors;
- cancellation;
- duplicate calls.

To izoluje błędy architektury od błędów Javy.

---

# 38. Etap 35 — pierwszy prawdziwy test end-to-end

Minimalny:

```text
GUI
 ↓
TXT
 ↓
Resolver
 ↓
OkapiBackend
 ↓
Bridge
 ↓
JVM
 ↓
PlainTextFilter
 ↓
TEXT_UNIT
 ↓
Translation
 ↓
Writer
 ↓
TXT
```

Kryteria:

- dokładnie jeden job;
- dokładnie jeden extraction;
- dokładnie jeden writer;
- jeden kontrolowany runtime;
- poprawny wynik;
- pełny cleanup.

---

# 39. Etap 36 — DOCX end-to-end

Analogicznie:

```text
GUI
 ↓
DOCX
 ↓
Resolver
 ↓
okf_openxml
 ↓
OpenXMLFilter
 ↓
events
 ↓
DocumentContract
 ↓
translation
 ↓
events
 ↓
IFilterWriter
 ↓
DOCX
```

Dodatkowo:

```text
source DOCX
 ↓
output DOCX
 ↓
ponowne otwarcie outputu
 ↓
extract
 ↓
contract validation
```

---

# 40. Etap 37 — performance

Mierzymy:

- czas startu JVM;
- czas extraction;
- czas mapping;
- czas translation;
- czas reconstruction;
- RAM;
- rozmiar IPC;
- liczbę eventów;
- liczbę TEXT_UNIT;
- czas per TEXT_UNIT;
- czas cold start;
- czas warm start.

Dopiero na tej podstawie decydujemy, czy host JVM powinien być:

```text
per job
```

czy:

```text
persistent worker
```

Wstępna rekomendacja:

> persistent host + izolowane joby, ale z kontrolowanym restartem po błędzie.

---

# 41. Etap 38 — walidacja końcowa

Przed uznaniem warstwy za gotową:

### Architecture

- brak zależności GUI → Java;
- brak zależności Translation Engine → Okapi classes;
- backend wymienny.

### Correctness

- TXT;
- DOCX;
- inline codes;
- skeleton;
- metadata;
- reconstruction.

### Reliability

- cancellation;
- timeout;
- crash;
- retry;
- cleanup.

### Security

- workspace isolation;
- path validation;
- resource limits.

### Performance

- brak niekontrolowanych startów;
- brak duplikatów;
- akceptowalny cold start;
- akceptowalny IPC.

### Verification

- unit;
- contract;
- integration;
- E2E;
- round-trip;
- differential.

---

# 42. Kryterium finalnego sukcesu

Warstwa jest gotowa dopiero, gdy poniższy scenariusz przechodzi:

```text
Użytkownik wybiera DOCX
        ↓
Resolver wybiera Okapi OpenXML
        ↓
powstaje dokładnie jeden Job
        ↓
Host JVM zostaje użyty zgodnie z lifecycle
        ↓
Okapi generuje eventy
        ↓
mapper tworzy DocumentContract V4
        ↓
Translation Engine tłumaczy jednostki
        ↓
mapper odtwarza eventy
        ↓
IFilterWriter tworzy DOCX
        ↓
output zostaje zwalidowany
        ↓
Job = COMPLETED
        ↓
host/session zostaje poprawnie zwolniony
```

A następnie:

```text
ten sam DOCX
→ Native backend
→ DocumentContract V4
```

może być porównany z:

```text
ten sam DOCX
→ Okapi backend
→ DocumentContract V4
```

bez zmiany Translation Engine.

---

# 43. Kolejność prac — skrócona mapa

```text
PHASE 0
Audyt obecnego kodu
        ↓
PHASE 1
Reverse engineering lifecycle
        ↓
PHASE 2
Okapi reference runner
        ↓
PHASE 3
Document Contract V4
        ↓
PHASE 4
Filter Execution Port
        ↓
PHASE 5
Capabilities + Registry
        ↓
PHASE 6
Resolver
        ↓
PHASE 7
Event Mapper
        ↓
PHASE 8
Mock Backend
        ↓
PHASE 9
IPC contract
        ↓
PHASE 10
Okapi Host
        ↓
PHASE 11
Okapi Backend
        ↓
PHASE 12
TXT E2E
        ↓
PHASE 13
DOCX E2E
        ↓
PHASE 14
Failure/Cancellation
        ↓
PHASE 15
Round-trip corpus
        ↓
PHASE 16
Native TXT
        ↓
PHASE 17
Differential testing
        ↓
PHASE 18
Native DOCX — później
```

---

# 44. Bramka decyzyjna przed implementacją

Przed pierwszym kodem należy zatwierdzić:

1. `DocumentContract V4`;
2. `FilterExecutionPort`;
3. `FilterCapabilities`;
4. IPC v1;
5. lifecycle Job;
6. lifecycle JVM;
7. model workspace;
8. event mapping;
9. TXT vertical slice;
10. DOCX vertical slice;
11. politykę crash/retry;
12. politykę persistent JVM;
13. corpus testowy;
14. Definition of Done.

Dopiero po tej bramce rozpoczynamy implementację.

---

# 45. Zasady nadrzędne

1. **Nie przenosić API Okapi do GUI.**
2. **Nie traktować `TextUnit` jako modelu domenowego aplikacji.**
3. **Nie rekonstruować dokumentu z samego tekstu.**
4. **Nie ignorować eventów bez jawnej decyzji.**
5. **Nie uruchamiać JVM z wielu miejsc aplikacji.**
6. **Nie tworzyć wielokrotnych jobów dla jednego żądania.**
7. **Nie instalować runtime automatycznie bez zgody użytkownika.**
8. **Nie zastępować Okapi native parserem przed utworzeniem testu referencyjnego.**
9. **Nie uznawać pliku output za poprawny bez walidacji.**
10. **Każda istotna decyzja ma mieć test lub dowód.**

---

# 46. Źródła i projekty referencyjne

## Oficjalne Okapi

- Okapi Framework: https://okapiframework.org/
- Filters: https://okapiframework.org/wiki/index.php/Filters
- Developer Guide — Getting Started: https://okapiframework.org/devguide/gettingstarted.html
- Developer Guide — Filters: https://okapiframework.org/devguide/filters.html
- Developer Guide — Pipelines: https://okapiframework.org/devguide/pipelines.html
- IFilter API: https://okapiframework.org/javadoc/net/sf/okapi/common/filters/IFilter.html
- RawDocument API: https://okapiframework.org/javadoc/net/sf/okapi/common/resource/RawDocument.html
- IFilterWriter API: https://okapiframework.org/javadoc/net/sf/okapi/common/filterwriter/IFilterWriter.html
- RawDocumentToFilterEventsStep: https://okapiframework.org/javadoc/net/sf/okapi/steps/common/RawDocumentToFilterEventsStep.html
- Okapi GitLab: https://gitlab.com/okapiframework/Okapi

## Projekty wykorzystujące Okapi

- Rainbow
- Tikal
- CheckMate
- Longhorn
- OmegaT Okapi Filters Plugin
- Okapi-ant
- Ocelot

Źródło:
https://gitlab.com/okapiframework/Okapi

## OmegaT

- Okapi Filters Plugin:
  https://okapiframework.org/wiki/index.php/Okapi_Filters_Plugin_for_OmegaT
- Plugin source:
  https://gitlab.com/okapiframework/omegat-plugin
- OmegaT:
  https://github.com/omegat-org/omegat

## Istotna obserwacja z projektów

Tikal i OmegaT potwierdzają praktyczny model:

```text
format
→ filter configuration
→ extraction
→ translation representation
→ merge/reconstruction
```

a konfiguracja filtra jest niezależnym elementem od samego rozszerzenia pliku.

---

# 47. Status pewności ustaleń

### CONFIRMED

- `IFilter` jest wspólnym API filtrów Okapi.
- `RawDocument` jest wejściowym zasobem filtra.
- filtr generuje eventy.
- `TEXT_UNIT` jest podstawowym eventem dla jednostek tekstowych.
- `IFilterWriter` odpowiada za output/reconstruction.
- filtry mają parametry.
- istnieje `IFilterConfigurationMapper`.
- Okapi ma konfiguracje takie jak `okf_openxml`.
- Okapi jest używane przez Rainbow, Tikal i plugin OmegaT.
- OpenXML Filter jest używany dla formatów Office.

### HIGH CONFIDENCE — decyzje architektoniczne

- JVM powinna być izolowana od GUI.
- DocumentContract powinien być niezależny od Okapi.
- Okapi powinno być backendem wykonawczym.
- event mapping powinien znajdować się na granicy adaptera.
- potrzebny jest centralny JobCoordinator.
- należy mieć reference corpus i differential testing.

### HYPOTHESIS — do potwierdzenia w repo/runtime

- dokładne miejsce obecnych wielokrotnych wywołań serwera;
- czy obecny projekt już posiada części DocumentContract V4;
- czy istniejący kod ma już częściowy bridge;
- czy persistent JVM będzie lepszy od per-job JVM dla obecnych dokumentów;
- które eventy i metadata są faktycznie wykorzystywane przez obecny konwerter.

---

# 48. Następny krok

**Nie zaczynać od implementacji bridge'a.**

Pierwszy krok wykonawczy:

```text
AUDYT REPO
   ↓
REVERSE ENGINEERING
   ↓
CURRENT STATE
   ↓
OKAPI REFERENCE RUNNER
   ↓
CONTRACT V4
```

Dopiero po tych pięciu krokach można bezpiecznie rozpocząć właściwą implementację `Filter Execution Layer`.

