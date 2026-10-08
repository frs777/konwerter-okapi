# Eksperymentalny port filtrów Okapi do Pythona

Ten katalog jest izolowanym obszarem badawczo-rozwojowym. Nie jest częścią aktywnego drzewa runtime Tłumacza i nie zmienia obecnego Filter Engine.

## Cel

Sprawdzić, czy semantykę wybranych filtrów Okapi można odtworzyć w Pythonie bez JVM, zachowując round-trip dokumentu, skeleton oraz kody inline.

## Pierwszy przypadek

`okapi_markdown_port` jest eksperymentalnym portem semantycznego wycinka Markdown Filter z Okapi 1.49.x. Nie jest deklarowaną implementacją 1:1.

Zakres pierwszego eksperymentu:

- dokument Markdown jako skeleton,
- fenced code jako treść nieprzetwarzalna,
- zwykły tekst jako jednostki tłumaczeniowe,
- inline code jako chroniony kod inline,
- proste linki/obrazy i znaczniki HTML jako kod inline,
- deterministyczny round-trip.

## Zasada

Najpierw testy i porównanie zachowania, następnie implementacja. Pozytywny wynik eksperymentu nie oznacza jeszcze możliwości usunięcia Javy z całego projektu.

## Stan badania 2026-10-06

Pierwszy etap portu Markdown został rozszerzony do **8 testów GREEN**. Prototyp ma jawne parametry dla bloków fenced, bloków wciętych i inline code oraz minimalny model eventów `START_DOCUMENT` / `TEXT_UNIT` / `DOCUMENT_PART` / `END_DOCUMENT`. Round-trip dla niezmienionych targetów jest potwierdzony.

Weryfikacja:

```text
PYTHONPATH=. python3 -m pytest -q okapi_markdown_port/tests
5 passed
python3 -m compileall -q okapi_markdown_port
PASS
```

Badanie z dokumentacji Okapi potwierdza, że `translateFencedCodeBlocks`, `translateIndentedCodeBlocks` i `translateInlineCodeBlocks` mają domyślnie wartość `true`; `translateUrls`, `translateHeaderMetadata` i `useCodeFinder` pozostają domyślnie wyłączone. citeturn0search0turn0search3

Ważne: GREEN oznacza zgodność tylko z naszym aktualnym, wąskim kontraktem eksperymentalnym. Nie oznacza zgodności z pełnym Markdown Filter. Następnym krokiem jest model zdarzeń Okapi (`START_DOCUMENT`, `TEXT_UNIT`, `DOCUMENT_PART`, `END_DOCUMENT`), pełniejszy model `TextFragment`/inline codes i differential testing względem JVM. Okapi definiuje właśnie taki strumień zdarzeń i rozdziela tekst od kodów inline. citeturn0search2turn0search10

Pełne ustalenia znajdują się w `reports/2026-10-06-raport-port-okapi-python.md`, a projekt architektury eksperymentu w `docs/ARCHITEKTURA.md`.
