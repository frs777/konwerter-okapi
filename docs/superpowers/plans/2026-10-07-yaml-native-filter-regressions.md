# YAML Native Filter Regression Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or **superpowers:executing-plans** to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Przywrócić dwa oczekiwane zachowania filtra YAML: brak nadmiarowego escapowania cudzysłowów w wartości double-quoted oraz zachowanie końcowego newline w literal block scalar.

**Architecture:** Naprawa pozostaje lokalna w `filters/yaml/filter.py`. Parser nadal korzysta z PyYAML i zachowuje oryginalne spany; zmieniamy wyłącznie kodowanie zmodyfikowanego scalara, bez zmiany procesu tłumaczenia ani modelu zdarzeń.

**Tech Stack:** Python 3, pytest, PyYAML, istniejący model `Event/TextUnit/TextFragment`.

**Spec:** Istniejące testy regresyjne w `tests/test_yaml_native_filter.py` są źródłem wymaganego zachowania.

## Global Constraints

- Nie zmieniać procesu tłumaczenia ani innych filtrów.
- Nie osłabiać istniejących testów.
- Stosować TDD: RED → minimalna poprawka → GREEN.
- Nie instalować nowych zależności.
- Zachować Java-free implementację filtra YAML.
- Po naprawie wykonać pełną regresję repozytorium; zatrzymać się na pierwszym nowym błędzie.

## Review Focus

- Double-quoted scalar zawierający cudzysłowy: zapis ma odpowiadać istniejącemu kontraktowi testu, bez dodatkowego escapowania.
- Literal block scalar kończący się newline: wynik musi zachować końcowy newline.
- Niezmienione wartości YAML: `round_trip()` nadal musi zwracać źródło dokładnie bez zmian.
- Komentarze i struktura dokumentu: writer nadal ma zastępować tylko span zmienionego scalara.
- Pozostałe style scalarów: pojedynczo cytowane i plain nie mogą zostać przypadkowo zmienione.

### Task 1: Naprawa double-quoted scalar

**Files:**
- Modify: `filters/yaml/filter.py:_encode_scalar`
- Test: `tests/test_yaml_native_filter.py::test_yaml_filter_preserves_quote_style_when_value_changes`

**Interfaces:**
- Consumes: `value: str`, `style: str | None`, `original: str`.
- Produces: YAML scalar replacement string zgodny z istniejącym testem.

- [ ] **Step 1: Potwierdzić RED na istniejącym teście**
Run: `python -m pytest -q tests/test_yaml_native_filter.py::test_yaml_filter_preserves_quote_style_when_value_changes`
Expected: FAIL z różnicą dotyczącą escapowania cudzysłowów.

- [ ] **Step 2: Zidentyfikować minimalną zmianę**
W `_encode_scalar` usunąć niepożądane JSON-owe escapowanie cudzysłowów dla tej ścieżki, zachowując otwierający/zamykający delimiter double-quoted i poprawne zachowanie dla wartości już zgodnych z parserem.

- [ ] **Step 3: Uruchomić test**
Run: `python -m pytest -q tests/test_yaml_native_filter.py::test_yaml_filter_preserves_quote_style_when_value_changes`
Expected: PASS.

### Task 2: Naprawa literal block scalar

**Files:**
- Modify: `filters/yaml/filter.py:_encode_scalar`
- Test: `tests/test_yaml_native_filter.py::test_yaml_filter_preserves_literal_block_structure_when_value_changes`

**Interfaces:**
- Consumes: `value` z zachowanym końcowym newline oraz oryginalny block scalar.
- Produces: blok `|` z zachowanym wcięciem i końcowym newline.

- [ ] **Step 1: Potwierdzić RED na istniejącym teście**
Run: `python -m pytest -q tests/test_yaml_native_filter.py::test_yaml_filter_preserves_literal_block_structure_when_value_changes`
Expected: FAIL przez brak końcowego newline.

- [ ] **Step 2: Zaimplementować minimalną poprawkę**
Zmienić konstrukcję treści tak, aby końcowy newline wynikający z `value` był zachowany, bez dodawania dodatkowych pustych linii.

- [ ] **Step 3: Uruchomić test**
Run: `python -m pytest -q tests/test_yaml_native_filter.py::test_yaml_filter_preserves_literal_block_structure_when_value_changes`
Expected: PASS.

### Task 3: Regresja filtra YAML

**Files:**
- Test: `tests/test_yaml_native_filter.py`

- [ ] **Step 1: Uruchomić cały zestaw YAML**
Run: `python -m pytest -q tests/test_yaml_native_filter.py`
Expected: wszystkie testy PASS.

### Task 4: Pełna weryfikacja repozytorium

- [ ] **Step 1: Uruchomić pełny pytest**
Run: `python -m pytest -q`
Expected: 0 failed.

- [ ] **Step 2: Sprawdzić kompilowalność**
Run: `python3 -m compileall -q core filters importer analyzer differential tools`
Expected: brak błędów.

- [ ] **Step 3: Sprawdzić status zmian**
Run: `git status --short`
Expected: tylko pliki związane z naprawą oraz plan/ewentualna dokumentacja, bez niezamierzonych zmian.

## Self-Review

- Spec coverage: oba zgłoszone błędy mają osobne testy i osobne kroki RED/GREEN.
- Step scan: każdy krok ma jeden sprawdzalny rezultat.
- Type consistency: wykorzystuje istniejącą sygnaturę `_encode_scalar(value, style, original)`.
- Review focus: obejmuje oba błędy oraz regresję round-trip i pozostałych stylów.
- Scope: brak zmian w tłumaczeniu, generatorze automatyzacji i innych filtrach.

