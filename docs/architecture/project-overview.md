# Architektura projektu — Okapi → Python

## Cel

Projekt B+R ma odtworzyć zachowanie filtrów Okapi jako niezależnych implementacji Pythonowych. Nie jest to mechaniczne tłumaczenie klas Java na Python. Implementacja docelowa ma zachować obserwowalne zachowanie filtrów, ale działać bez JVM w produkcyjnym runtime.

## Pipeline badawczy

```text
Okapi JAR / metadane / źródła referencyjne
                  |
                  v
       Inspekcja i analiza statyczna
                  |
                  v
    Java Probe / dowody refleksyjne
                  |
                  v
       Ekstrakcja zachowania
                  |
                  v
            Filter IR
                  |
                  v
      Generator / implementacja Python
                  |
                  v
          Python Filter Core
                  |
                  v
     Differential + round-trip tests
```

Źródła Java mogą być analizowane, a uruchomienie oryginalnego filtra jest dozwolone w kontrolowanym środowisku badawczym, jeśli jest potrzebne do zebrania danych referencyjnych. Żaden z tych mechanizmów nie może być ukrytym wymaganiem produkcyjnego rdzenia Python.

## Główne obszary kodu

| Obszar | Ścieżka | Odpowiedzialność |
|---|---|---|
| Model dokumentu i zdarzeń | `core/document/`, `core/events/` | neutralna reprezentacja dokumentu, fragmentów i zdarzeń |
| Kontrakt filtra | `core/filter.py`, `core/reader/`, `core/writer/` | cykl życia odczytu i zapisu |
| Filter IR | `filter_ir/` | model pośredni i normalizacja deklaracji filtra |
| Analyzer | `analyzer/` | inspekcja JAR, klasy, zależności, źródła i dowody Java |
| Importer/generator | `importer/` | ekstrakcja, tworzenie IR, generowanie szkieletu filtra i raportu |
| Natywne filtry | `filters/` | niezależne implementacje Python dla formatów |
| Execution layer | `execution/` | rejestr, rozpoznawanie filtra, backend i usługa wykonawcza |
| Testy różnicowe | `differential/` | normalizacja, porównanie i raport różnic |
| Narzędzia CLI | `tools/` | inspekcja JAR oraz uruchamianie pipeline konwersji |
| Materiały referencyjne | `testdata/okapi-filters-java/` | lokalne JAR-y i metadane filtrów do badań |

## Dwie różne ścieżki

### 1. Konwersja i badanie filtra

`tools/okapi_convert.py` uruchamia pipeline `JAR + filter.json → ekstrakcja → Filter IR → generator Python → raport`. W zależności od dostępnych materiałów ekstrakcja może korzystać z metadanych i analizy źródeł. Wygenerowany pakiet jest punktem startowym, a nie automatycznym dowodem kompletności.

### 2. Wykonanie dokumentu w Pythonie

`execution/native_catalog.py` tworzy rejestr natywnych filtrów i backend Python. `ExecutionService` rozwiązuje żądanie, wybiera filtr i koordynuje wykonanie. To osobny przepływ od analizy JAR. Rejestracja filtra nie gwarantuje jeszcze pełnej zgodności z Okapi.

## Granice modelu dokumentowego

Filtr nie jest funkcją `str -> str`. Musi potencjalnie reprezentować:

- strumień zdarzeń i kolejność zdarzeń;
- wiele jednostek tłumaczeniowych z identyfikatorami i metadanymi;
- fragmenty tekstowe oraz kody inline sparowane, izolowane lub chronione;
- skeleton i elementy strukturalne wymagane przy zapisie;
- zasoby wieloczęściowych kontenerów i relacje między nimi;
- konfigurację wpływającą na translatability, segmentację i zapis.

Uproszczenie któregoś z tych elementów wymaga dowodu, że dany format i zakres użycia na tym nie tracą.

## Zasady architektoniczne

1. Najpierw ustal zachowanie referencyjne, potem projektuj implementację Python.
2. Używaj Javy do pozyskiwania dowodów wtedy, gdy daje to najszybszą i najpewniejszą odpowiedź.
3. Rozdzielaj metadane deklaratywne, statyczną analizę kodu, wynik refleksji i rzeczywiste zachowanie na plikach.
4. Utrzymuj jeden jawny kontrakt Filter IR i testuj jego walidację.
5. Dodawaj test regresyjny dla każdej wykrytej rozbieżności.
6. Oddzielaj status „wygenerowano” od „działa” i „zgodne z Okapi”.
7. Nie modyfikuj repozytorium źródeł referencyjnych Okapi ani projektu Tłumacz podczas prac w tym repozytorium.
