# Narzędzia developerskie i polecenia

## Środowisko

Konfiguracja projektu w `pyproject.toml` deklaruje Python `>=3.11`, pytest i katalog `tests/`. Projekt korzysta także z Javy w wybranych narzędziach badawczych; aktualne testy Java Probe wymagają dostępnych poleceń `javac` i `java`.

Sprawdzenie środowiska z katalogu głównego repozytorium:

```sh
python --version
python -m pytest --version
java -version
javac -version
git status --short
```

Nie instaluj pakietów systemowych, JDK ani innych zależności bez zgody użytkownika. Brak JDK blokuje Java Probe, ale sam w sobie nie oznacza, że natywne filtry Python są niesprawne.

## Główne narzędzia

| Narzędzie | Zastosowanie | Czy uruchamia kod Java? |
|---|---|---|
| `tools/okapi_inspect.py` | odczyt manifestu i listy klas z archiwum JAR | Nie |
| `analyzer.jar_inspector.JarInspector` | inspekcja struktury ZIP/JAR i manifestu | Nie |
| `analyzer.class_inspector` | analiza struktury klas | sprawdzić implementację danego wywołania |
| `analyzer.java_probe.JavaFilterProbe` | refleksja nad klasą filtra i analiza classpath | Tak: kompiluje i uruchamia mały program Java |
| `analyzer.metadata.source_extractor` | wydobywanie sygnałów zachowania z kodu źródłowego Java | Nie wymaga uruchomienia badanego filtra |
| `tools/okapi_convert.py` | pipeline JAR/metadata → Filter IR → pakiet Python | może korzystać z Java Probe, jeśli wywołany pipeline tego wymaga |
| `pytest` | testy modelu, filtrów, generatora i integracji | zależy od konkretnego testu |

## Inspekcja JAR

```sh
python tools/okapi_inspect.py testdata/okapi-filters-java/markdown/runtime-markdown-1.49.0-SNAPSHOT.jar
```

Narzędzie odczytuje manifest i nazwy klas z archiwum. Nie uruchamia kodu z JAR. To dobry pierwszy krok, gdy trzeba poznać zawartość pakietu bez wykonywania jego implementacji.

## Konwersja pojedynczego filtra

```sh
python tools/okapi_convert.py \
  testdata/okapi-filters-java/markdown/runtime-markdown-1.49.0-SNAPSHOT.jar \
  --metadata testdata/okapi-filters-java/markdown/filter.json \
  --output ./converted
```

Wariant z analizą źródeł Okapi:

```sh
python tools/okapi_convert.py \
  testdata/okapi-filters-java/markdown/runtime-markdown-1.49.0-SNAPSHOT.jar \
  --metadata testdata/okapi-filters-java/markdown/filter.json \
  --source-root /ścieżka/do/źródeł/Okapi \
  --output ./converted
```

Ścieżkę `--source-root` należy podać tylko wtedy, gdy rzeczywiście dostępne są źródła w oczekiwanym układzie. Brak tego argumentu powoduje pominięcie analizy zachowania źródłowego, co narzędzie sygnalizuje w dokumentacji CLI.

## Konwersja katalogu filtrów

```sh
python tools/okapi_convert.py \
  --catalog testdata/okapi-filters-java \
  --output ./converted
```

Katalog wejściowy powinien zawierać podkatalogi z `filter.json` i pasującymi plikami `runtime-<nazwa>-*.jar`. Sprawdź wynik i raport każdego filtra; status `generated` oznacza wygenerowanie artefaktów, nie pełną zgodność funkcjonalną.

## Testy

Testy celowane:

```sh
python -m pytest -q tests/test_filter_ir.py
python -m pytest -q tests/test_jar_analyzer.py
python -m pytest -q tests/test_java_filter_probe.py
python -m pytest -q tests/test_java_evidence_pipeline.py
python -m pytest -q tests/test_automatic_conversion.py
```

Nie wszystkie ścieżki testowe są niezależne od lokalnego środowiska. Test Java Probe może korzystać z JAR-ów i źródeł referencyjnych umieszczonych w konkretnych ścieżkach. Przed uruchomieniem na innej maszynie sprawdź fixture'y i ścieżki bezwzględne w teście.

Po zmianie kodu:

```sh
git diff --check
python -m pytest -q <testy-zmienianego-obszaru>
```

Następnie uruchom powiązane testy integracyjne. Raportuj tylko komendy rzeczywiście uruchomione i ich rzeczywisty wynik.

## Praca w repozytorium

```sh
git status --short
git diff --stat
git diff -- docs/
```

Repozytorium może zawierać niezacommitowane zmiany użytkownika i pliki robocze. Nie resetuj repozytorium, nie przywracaj plików i nie usuwaj artefaktów, które nie powstały w bieżącej operacji.
