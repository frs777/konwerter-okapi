# Konwerter Okapi

Niezależny projekt B+R mający na celu odtworzenie zachowania filtrów Okapi w Pythonie i wyeliminowanie zależności od JVM z produkcyjnego rdzenia filtrów.

## Cel

Pipeline docelowy:

okapi-filter.jar -> Analyzer -> Filter IR -> generator Python -> Python Filter Core -> differential testing -> round-trip

Java/Okapi może być używana wyłącznie jako tymczasowy wzorzec porównawczy podczas migracji. Produkcyjny Python Filter Core nie może wymagać JVM.

## Materiały badawcze

- OKAPI_PYTHON_PROJECT_KONCEPCJA.md — zatwierdzona koncepcja projektu.
- research/filtry-python-prototyp/ — poprzedni eksperymentalny port Markdown.
- testdata/okapi-filters-java/ — kopia aktualnych pakietów filtrów Okapi z projektu Tłumacz, używana jako materiał referencyjny/testowy.

Pierwszym filtrem referencyjnym jest Markdown.
## Automatyczna konwersja filtra Okapi

Podstawowy pipeline konwersji działa przez analizę JAR, ekstrakcję metadanych i zachowania źródłowego, wygenerowanie Filter IR oraz utworzenie pakietu Pythonowego:

```bash
python tools/okapi_convert.py \
  testdata/okapi-filters-java/markdown/runtime-markdown-1.49.0-SNAPSHOT.jar \
  --metadata testdata/okapi-filters-java/markdown/filter.json \
  --output ./converted
```

Pipeline tworzy `filter.py`, `filter_ir.json`, `conversion_report.json` i `__init__.py`. Jest to fundament automatycznej migracji: analiza i IR są automatyczne, natomiast zachowanie parsera/specyficzne adaptery filtra są jeszcze rozwijane i muszą być potwierdzane testami round-trip oraz differential testing.

