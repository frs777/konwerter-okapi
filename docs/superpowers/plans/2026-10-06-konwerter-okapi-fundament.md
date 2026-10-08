# Konwerter Okapi Fundament Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Zbudować niezależny, testowalny fundament Pythonowego rdzenia filtrów Okapi oraz zweryfikować go na złożonym filtrze DOCX/OpenXML; Markdown pozostaje wyłącznie smoke testem.

**Architecture:** Analyzer, formalny Filter IR, Python Filter Core, importer/generator oraz differential testing. Java/Okapi pozostaje wyłącznie oracle podczas migracji.

**Tech Stack:** Python 3.11+, pytest, standardowa biblioteka; dodatkowe biblioteki zostaną dobrane później, bez automatycznej instalacji.

**Spec:** OKAPI_PYTHON_PROJECT_KONCEPCJA.md

## Global Constraints

- Python Filter Core nie może wymagać JVM.
- Inline code jest strukturą modelu, nie tekstowym markerem.
- Analizujemy zachowanie, nie kopiujemy implementacji Java.
- Nowa logika jest rozwijana TDD.
- Differential testing i round-trip są kryteriami gotowości filtra.
- Dokumentacja jest aktualizowana po zmianach.

## Review Focus

- Inline code nie może zostać potraktowany jako zwykły tekst.
- Skeleton musi umożliwiać odtworzenie dokumentu.
- Treść filtrowana i chroniona musi być rozróżnialna.
- Unicode i puste jednostki nie mogą powodować utraty danych.
- Błędne wejście kończy się kontrolowanym błędem.

### Zadanie 1: Model dokumentu i zdarzeń

**Files:** core/document/model.py, core/events/model.py, tests/test_document_model.py, tests/test_events_model.py

- [ ] Napisz failing tests dla TextUnit, TextFragment, Code, Skeleton i zdarzeń.
- [ ] Potwierdź RED.
- [ ] Zaimplementuj minimalne typowane modele.
- [ ] Potwierdź GREEN.

### Zadanie 2: Kontrakt Filter IR

**Files:** filter_ir/model/filter.py, filter_ir/schema/filter.schema.json, tests/test_filter_ir.py

- [ ] Napisz test poprawnego IR filtra Markdown.
- [ ] Napisz test odrzucenia niepełnego IR.
- [ ] Potwierdź RED.
- [ ] Zaimplementuj minimalny model i walidator.
- [ ] Potwierdź GREEN.

### Zadanie 3: Minimalny Python Filter Core

**Files:** core/reader/base.py, core/writer/base.py, core/filter.py, tests/test_filter_core.py

- [ ] Napisz failing test cyklu reader -> events -> writer.
- [ ] Potwierdź RED.
- [ ] Zaimplementuj minimalny kontrakt filtra.
- [ ] Potwierdź GREEN.

### Zadanie 4: Markdown jako smoke test

**Files:** filters/markdown/, fixtures/markdown/, tests/test_markdown_smoke.py

- [ ] Utrzymaj minimalny fixture tekstowy jako test bazowego Reader/Writer i podstawowego TextUnit.
- [ ] Napisz failing test prostego round-trip.
- [ ] Potwierdź RED.
- [ ] Zaimplementuj minimalny adapter smoke test.
- [ ] Potwierdź GREEN.

### Zadanie 5: DOCX/OpenXML jako pierwszy pełny filtr referencyjny

**Files:** filters/docx/, fixtures/docx/, tests/test_docx_reference.py

- [ ] Zidentyfikuj minimalny fixture DOCX obejmujący akapit, wiele runów, hyperlink, tabelę, nagłówek/stopkę i element nietłumaczalny.
- [ ] Napisz failing tests oczekiwanych TextUnitów, inline Code, protected content i skeletonu.
- [ ] Potwierdź RED.
- [ ] Zaimplementuj minimalny parser/reader DOCX bez JVM.
- [ ] Potwierdź GREEN.
- [ ] Dodaj writer i round-trip test.
- [ ] Rozszerz fixture o przypadki Unicode, puste elementy i zagnieżdżenia.

### Zadanie 6: Analyzer JAR

**Files:** analyzer/jar_inspector/inspector.py, analyzer/metadata/extractor.py, analyzer/dependencies/analyzer.py, tests/test_jar_analyzer.py

- [ ] Napisz failing tests identyfikacji JAR, manifestu, klas i zależności.
- [ ] Potwierdź RED.
- [ ] Zaimplementuj analizę JAR bez używania go jako produkcyjnego runtime.
- [ ] Potwierdź GREEN na testdata/okapi-filters-java/markdown/.

### Zadanie 7: Differential testing

**Files:** differential/event_normalizer/normalizer.py, differential/comparator/comparator.py, differential/reports/report.py, tests/test_differential.py

- [ ] Zdefiniuj normalizację wyników Java/Okapi i Python.
- [ ] Napisz failing test identycznego strumienia zdarzeń.
- [ ] Potwierdź RED.
- [ ] Zaimplementuj comparator i raport różnic.
- [ ] Potwierdź GREEN.

### Zadanie 8: Generator i importer

**Files:** importer/extraction/, importer/ir_generation/, importer/python_generation/, tests/test_importer_pipeline.py

- [ ] Zdefiniuj fixture IR odpowiadający Markdown.
- [ ] Napisz failing test IR -> Python.
- [ ] Potwierdź RED.
- [ ] Zaimplementuj minimalny generator.
- [ ] Potwierdź GREEN.
- [ ] Dodaj raport elementów wymagających adaptera.

### Zadanie 9: Weryfikacja

- [ ] Uruchom cały pytest.
- [ ] Uruchom kompilację modułów Python.
- [ ] Wykonaj differential test Markdown.
- [ ] Wykonaj round-trip Markdown.
- [ ] Zaktualizuj docs/STATUS.md.
- [ ] Zapisz wynik i ograniczenia w raporcie.
