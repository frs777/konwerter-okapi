# AGENTS.md

## Cel projektu

Celem projektu `konwerter-okapi` jest opracowanie niezależnego od JVM, pythonowego rdzenia filtrów Okapi oraz narzędzi do analizy, migracji i walidacji ich zachowania, w tym zestawu skryptów umożliwiających automatyczną konwersję filtrów Okapi do niezależnych filtrów Pythonowych.

Docelowy przepływ:

`analiza Okapi/JAR/bytecode → Filter IR → importer/generator → implementacja Python → differential testing → round-trip testing`

Najważniejszy cel techniczny: uzyskać rzeczywistą zgodność obserwowalnego zachowania filtrów Okapi bez zależności JVM w produkcyjnym runtime.

## Zasady pracy agenta

- Kontynuuj pracę autonomicznie przez kolejne etapy, jeżeli wymagania są już określone.
- Nie zatrzymuj pracy pośrednimi pytaniami o zgodę na następny etap.
- Stosuj TDD: RED → minimalna implementacja → GREEN → refaktoryzacja → świeża weryfikacja.
- Przed deklaracją ukończenia wykonuj świeżą regresję oraz wymagane kontrole.
- Wszystkie istotne zmiany zapisuj w `docs/STATUS.md`.
- Wykonuj backup przed większymi zmianami.
- Nie modyfikuj `/home/frs/Projekty/tlumacz-v4`.
- `/home/frs/Projekty/Okapi-main` traktuj jako źródło referencyjne i nie modyfikuj tego katalogu.
- Nie instaluj pakietów systemowych, Maven, JDK ani innych zależności bez wyraźnej zgody użytkownika.
- Nie kopiuj mechanicznie implementacji Java. Analizuj zachowanie i odtwarzaj je niezależnie w Pythonie.
- JVM może być używana jako tymczasowy oracle/differential test, ale nie może być zależnością produkcyjnego Python Filter Core.

## Pliki tymczasowe i `.bak`

- Po zakończeniu każdej operacji usuwaj powstałe pliki `.bak` oraz inne niezamierzone kopie tymczasowe.
- Przed usunięciem sprawdź, czy `.bak` nie jest jedyną kopią istotnych danych.
- Nie usuwaj świadomie utworzonych backupów projektu w katalogu `backups/` ani nazwanych archiwów backupowych.
- Pliki tymczasowe utworzone wyłącznie podczas edycji lub testowania powinny zostać usunięte po zakończeniu etapu.

## Priorytet końcowy

Doprowadzić projekt do rzeczywistego, zweryfikowanego PoC end-to-end: niezależny Python Filter Core, formalny Filter IR, analyzer, importer/generator, działające filtry referencyjne, differential testing, round-trip testing, dokumentacja oraz brak JVM w produkcyjnym runtime.
