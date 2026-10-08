# Dokumentacja Konwertera Okapi

Ta dokumentacja dotyczy samodzielnego repozytorium `konwerter-okapi`. Jest utrzymywana razem z kodem i ma opisywać stan potwierdzony implementacją, narzędziami oraz testami.

## Zacznij tutaj

- [Cel i architektura](architecture/project-overview.md) — docelowy pipeline oraz podział odpowiedzialności.
- [Silnik wykonawczy — stan bieżący](architecture/okapi-execution-current-state.md) — obecny kod, integracja filtrów i ograniczenia.
- [Specyfikacja zachowania filtrów](architecture/okapi-filter-replacement-rules.md) — kontrakt do odtworzenia niezależnie od JVM.
- [Narzędzia developerskie](tools/development-tools.md) — środowisko, komendy i procedury weryfikacji.
- [Inspekcja JAR i Java Probe](tools/java-analysis.md) — co potrafią narzędzia analizujące kod Okapi.
- [Testy różnicowe i round-trip](testing/differential-testing.md) — jak oceniać zgodność implementacji Python z referencją.
- [Inwentaryzacja filtrów](filters/inventory.md) — aktualny rejestr natywnych implementacji i luki do weryfikacji.
- [Licencje](LICENSING.md) — istniejący audyt licencyjny.

## Zasada nadrzędna

Celem jest odtworzenie obserwowalnej funkcjonalności filtrów Okapi w Pythonie. Java, JAR-y, bytecode i źródła Okapi mogą być używane jako narzędzia badawcze i oracle porównawczy. Produkcyjny Python Filter Core nie może wymagać JVM.

Nie uznajemy filtra za zgodny tylko dlatego, że istnieje klasa Python lub test jednostkowy przechodzi. Zgodność wymaga dowodów dotyczących ekstrakcji, struktury, segmentacji, kodów inline, metadanych, zapisu i round-trip.

## Jak czytać statusy

- **Potwierdzone w kodzie** — można wskazać konkretny plik i funkcję.
- **Przetestowane** — istnieje test i odnotowano świeży wynik jego uruchomienia.
- **Zgodność częściowa** — działa część kontraktu, lecz nie ma kompletnego dowodu równoważności.
- **Zgodne** — wynik potwierdzony testami różnicowymi oraz walidacją round-trip dla zdefiniowanego zakresu.
- **Plan** — zamierzona praca, nie stan bieżący.

Dokumenty nie powinny przedstawiać planu ani wyniku historycznego jako bieżącego faktu. Każda istotna zmiana kodu powinna aktualizować odpowiedni dokument i `docs/STATUS.md`.

## Referencje implementacyjne

- [Python Filter Core i Filter IR](architecture/filter-core-and-ir.md) — lifecycle, model dokumentu, eventy i kontrakt IR.
- [Workflow portowania filtra](architecture/filter-porting-workflow.md) — od analizy JAR-a do implementacji Python i walidacji.
- [Macierz zgodności](architecture/filter-compatibility-matrix.md) — zarejestrowane formaty i wymagane dowody zgodności.
