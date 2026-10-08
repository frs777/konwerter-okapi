# Analiza JAR, klas Java i zachowania filtrów

## Cel narzędzi Java

Java jest w tym projekcie źródłem dowodów do odtworzenia zachowania filtrów Okapi. Nie jest wymagana w docelowym runtime produkcyjnego Python Filter Core. Narzędzia mają odpowiedzieć na różne pytania; nie należy traktować ich wyników jako zamiennych.

## Poziomy dowodów

| Poziom | Metoda | Co można wywnioskować | Czego nie dowodzi |
|---|---|---|---|
| Zawartość JAR | ZIP + manifest | nazwa pakietu, metadane manifestu, nazwy klas | zachowanie filtra |
| Sygnatury klas | inspekcja class/bytecode | klasy, metody i struktura dostępna w analizie | semantyka metod w każdym kontekście |
| Analiza źródeł | `JavaSourceBehaviorExtractor` | sygnały z kodu, parametry, lifecycle i reguły rozpoznane przez ekstraktor | pełne zachowanie wykonawcze; heurystyki mogą coś pominąć |
| Refleksja runtime | `JavaFilterProbe` | nadklasa, interfejsy, konstruktory, metody, zależności i braki classpath | wynik ekstrakcji dokumentu |
| Test referencyjny | uruchomienie oryginalnego filtra na fixture | obserwowalne eventy, jednostki, markery i metadane dla danego przypadku | zgodność dla nieprzetestowanych przypadków |

## 1. Inspektor JAR

Kod: `analyzer/jar_inspector/inspector.py`, CLI: `tools/okapi_inspect.py`.

Inspektor otwiera JAR jako archiwum ZIP, odczytuje `META-INF/MANIFEST.MF` (jeśli istnieje) i zbiera nazwy klas `.class`. Nie wykonuje klas z badanego JAR-a.

```sh
python tools/okapi_inspect.py ścieżka/do/runtime-filter.jar
```

## 2. Java Filter Probe

Kod: `analyzer/java_probe/probe.py` oraz `analyzer/java_probe/JavaFilterProbe.java`.

Probe kompiluje mały introspektor do katalogu tymczasowego, a następnie uruchamia go z JAR-em filtra i wskazanym classpath. Wynik JSON jest mapowany do struktur `JavaEvidence` i `JavaMethod`. Wynik obejmuje m.in.:

- pełną nazwę klasy, nadklasę i interfejsy;
- sygnatury metod i konstruktory;
- listę publicznych metod;
- klasy referencjonowane;
- JAR-y classpath i rozwiązane zależności;
- brakujące klasy oraz flagę kompletności refleksji.

Przykładowe użycie w Pythonie:

```python
from pathlib import Path
from analyzer.java_probe.probe import JavaFilterProbe

evidence = JavaFilterProbe().probe(
    Path("testdata/okapi-filters-java/openxml/runtime-openxml-1.49.0-SNAPSHOT.jar"),
    "net.sf.okapi.filters.openxml.OpenXMLFilter",
    classpath=[Path("ścieżka/do/okapi-core.jar")],
)
print(evidence.class_name)
print(evidence.interfaces)
print(evidence.missing_classes)
```

Probe uruchamia `javac` i `java`, dlatego wymaga JDK oraz kompletu zależności potrzebnych do refleksji. Brak klasy w classpath może dać niekompletny wynik; zawsze sprawdzaj `missing_classes` i `reflection_complete`.

## 3. Ekstrakcja zachowania ze źródeł

Kod: `analyzer/metadata/source_extractor.py`.

Ekstraktor analizuje tekst źródłowy Java, poszukując m.in. deklaracji klas, metod lifecycle, rozszerzeń, parametrów, cech i reguł tokenów. Jest to analiza statyczna oparta na wzorcach, więc wyniki są wskazówkami do IR i dalszych testów, nie autorytatywnym opisem zachowania.

W szczególności:
- sygnatura metody nie mówi, kiedy i jak metoda zmienia stan;
- znaleziony parametr nie dowodzi, że wpływa na aktualny przypadek;
- brak wykrytej reguły nie dowodzi braku funkcjonalności;
- komentarze, helpery, dziedziczenie i konfiguracja mogą wpływać na rezultat.

## 4. Zbieranie zachowania referencyjnego

Aby odtworzyć rzeczywiste działanie, przygotuj fixture i uruchom oryginalny filtr w kontrolowanym środowisku referencyjnym. Zapisz wejściową konfigurację oraz znormalizowany wynik: typy i kolejność eventów, jednostki, źródło/target, fragmenty inline, metadata, skeleton i błędy.

Porównuj nie tylko tekst. Dwa filtry zwracające ten sam tekst, ale gubiące link, kod inline, styl lub strukturę dokumentu, nie są równoważne.

## 5. Wynik analizy i Filter IR

Każdy wyeksportowany fakt powinien mieć pochodzenie: manifest, metadata JSON, źródło, refleksja albo test runtime. Przydatny raport powinien rozdzielać:
- fakty bezpośrednio odczytane;
- wnioski heurystyczne;
- hipotezy wymagające fixture;
- nierozwiązane zależności;
- funkcje, których nie udało się zanalizować.

Nie ukrywaj niekompletności. Lepiej wygenerować jawny adapter częściowy niż oznaczyć filtr jako zgodny na podstawie niepełnych danych.
