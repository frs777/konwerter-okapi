# Workflow: od filtra Okapi do niezależnej implementacji Python

## Cel

Procedura prowadzi od JAR-a filtra i dostępnych źródeł do natywnej implementacji Python, której zachowanie zostało porównane z referencją. Automatyzacja przyspiesza zbieranie informacji i generowanie szkieletu, ale nie zastępuje dowodów funkcjonalnych.

## 1. Ustal źródła i ich wersje

Dla każdego filtra zapisz:
- JAR oraz wersję artefaktu;
- odpowiadający mu `filter.json`;
- wersję/commit źródeł Okapi, jeżeli są dostępne;
- zależności i konfiguracje filtra;
- formaty wejściowe oraz zestaw fixture;
- parametry, które mają wejść do zakresu zgodności.

Nie zakładaj zgodności wersji na podstawie podobnej nazwy pliku. Niezgodność wersji JAR-a, źródła i metadanych musi być widoczna w raporcie.

## 2. Zrób bezpieczną inspekcję JAR-a

`JarInspector` w `analyzer/jar_inspector/inspector.py` czyta manifest i listę klas archiwum. Nie wykonuje badanego kodu.

```sh
python tools/okapi_inspect.py \
  testdata/okapi-filters-java/markdown/runtime-markdown-1.49.0-SNAPSHOT.jar
```

Wykorzystaj wynik do potwierdzenia nazwy klasy/artefaktu oraz pakietów. Sama lista klas nie dostarcza zasad segmentacji ani semantyki readera/writera.

## 3. Wyodrębnij metadane deklaratywne

`FilterMetadataExtractor` w `analyzer/metadata/extractor.py` odczytuje `filter.json`. Obecny kontrakt wymaga pól `name` i `entry_class`; zależności są pobierane z elementów `dependencies[].artifact`.

Przed dalszą analizą sprawdź, czy wskazana klasa faktycznie występuje w JAR-ze i czy plik metadanych odpowiada badanemu artefaktowi.

## 4. Zbierz statyczne i runtime evidence

`JavaSourceBehaviorExtractor` w `analyzer/metadata/source_extractor.py` przeszukuje kod źródłowy i heurystycznie zbiera sygnały o klasie, lifecycle, rozszerzeniach, parametrach i cechach. Nie jest to pełna analiza przepływu sterowania. Brak znalezionej reguły nie oznacza braku funkcji.

Opcjonalnie `JavaFilterProbe` (w `analyzer/java_probe/probe.py`) kompiluje pomocniczą klasę introspekcyjną, a następnie uruchamia ją przez `java` z JAR-em i classpathem. Daje m.in. nadklasę, interfejsy, metody, konstruktory oraz wykryte brakujące klasy. Wymaga `javac`, `java` i zależności potrzebnych do refleksji.

Oddziel w raporcie:
- fakty odczytane z metadanych/JAR;
- heurystyki z analizy źródła;
- fakty z refleksji runtime;
- wynik zachowania na dokumentach;
- niewiadome i nierozwiązane zależności.

Jeżeli probe nie zadziała, importer może pozostać przy innych źródłach danych. Brak wyniku nie może zostać przedstawiony jako potwierdzenie braku funkcji.

## 5. Utwórz i przejrzyj Filter IR

`importer/ir_generation/generator.py` mapuje `ExtractedFilter` na model `FilterIR`. Sprawdź m.in.:

- formaty, MIME i rozszerzenia;
- parametry zadeklarowane, ich typy, defaulty oraz parametry rzeczywiście używane;
- reguły tokenów i strategie markup;
- wymagane cechy;
- pochodzenie `entry_class`, lifecycle i dowodów Java;
- pola, które pozostały nieznane.

IR ma być użytecznym kontraktem dla implementacji i walidacji, a nie tylko dokumentem opisowym.

## 6. Wygeneruj kandydata implementacji

CLI:

```sh
python tools/okapi_convert.py \
  testdata/okapi-filters-java/markdown/runtime-markdown-1.49.0-SNAPSHOT.jar \
  --metadata testdata/okapi-filters-java/markdown/filter.json \
  --output ./converted-markdown
```

Gdy źródła Okapi faktycznie są dostępne:

```sh
python tools/okapi_convert.py \
  testdata/okapi-filters-java/markdown/runtime-markdown-1.49.0-SNAPSHOT.jar \
  --metadata testdata/okapi-filters-java/markdown/filter.json \
  --source-root /sciezka/do/Okapi-main/okapi/filters \
  --output ./converted-markdown
```

Ścieżka `--source-root` jest przykładowa i musi wskazywać realny katalog ze źródłami. Tryb katalogowy:

```sh
python tools/okapi_convert.py \
  --catalog testdata/okapi-filters-java \
  --output ./converted-catalog
```

Pipeline znajduje się w `importer/pipeline.py`, a generator w `importer/python_generation/generator.py`. Zgodnie z README artefakty obejmują `filter.py`, `filter_ir.json`, `conversion_report.json` i `__init__.py`.

Przejrzyj raport i wygenerowany kod przed wykonaniem testów. Generator może utworzyć adapter do istniejącego filtra, implementację regułową albo ogólny szkielet. Stan `generated` znaczy, że artefakty powstały — nie, że odtworzono pełną semantykę Okapi.

## 7. Uzupełnij zachowanie w Pythonie

Dla konkretnego formatu należy zaimplementować lub potwierdzić:
- składnię i strukturę dokumentu;
- wybór tłumaczalnych oraz chronionych części;
- segmentację i konteksty;
- typy inline codes, ID, parowanie i reguły ich przemieszczania;
- metadata, skeleton i relacje zasobów;
- wszystkie parametry należące do deklarowanego zakresu;
- zapis dokumentu, walidację i obsługę błędów.

Nie kopiuj mechanicznie implementacji Java. Zbieraj jej zachowanie jako dowód, a następnie odtwarzaj je za pomocą modelu i parsera Python.

## 8. Testuj różnicowo i round-trip

`EventNormalizer` oraz `DifferentialComparator` znajdują się w `differential/`. Obecny normalizator serializuje typ i zasób eventu; przed użyciem wyniku jako bramki zgodności upewnij się, że porównanie obejmuje wszystkie właściwości istotne dla formatu i nie pomija markup/skeleton.

Każdy filtr weryfikuj osobno pod kątem:
1. typów/kolejności eventów;
2. liczby, kolejności, ID, source/target i metadanych jednostek;
3. inline codes, zagnieżdżenia i treści chronionej;
4. parametrów domyślnych oraz wybranych konfiguracji;
5. niezmienionego round-trip;
6. round-trip po zmianie wyłącznie tłumaczalnej zawartości;
7. błędnego wejścia, nieobsługiwanej opcji i brakujących zależności.

Nie normalizuj różnic strukturalnych tylko po to, aby test przechodził.

## 9. Kryterium akceptacji

Filtr może być oznaczony jako **zweryfikowany w zakresie X** dopiero wtedy, gdy raport wskazuje:
- wersję referencyjną i konfigurację;
- listę fixture oraz cechy, które pokrywają;
- pełną komendę testową i wynik;
- różnice i ich klasyfikację;
- walidację round-trip;
- ograniczenia, które nadal pozostają.

Jeden test jednostkowy albo poprawny wygenerowany plik nie uzasadniają deklaracji pełnej zgodności formatu.
