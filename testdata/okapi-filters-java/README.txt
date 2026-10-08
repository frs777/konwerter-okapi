Magazyn filtrów Tłumacza V4.

W bieżącej wersji deweloperskiej aplikacja wskazuje ten katalog jako domyślny magazyn filtrów.
Docelowy magazyn użytkownika: /home/frs/.config/tlumacz/filters

Kontrakt pakietu filtra:

  filters/<nazwa>/filter.json
  filters/<nazwa>/*.jar

Minimalny descriptor `filter.json`:

  {
    "name": "openxml",
    "entry_class": "net.sf.okapi.filters.openxml.OpenXMLFilter"
  }

Filter Host tworzy dla konkretnego pakietu izolowany `URLClassLoader` dopiero przy pierwszym użyciu filtra. Po zamknięciu sesji dokumentu zamykany jest również loader.

Bieżące pakiety w repozytorium używają symlinków do istniejących artefaktów `okapi-runtime`. Jest to etap przejściowy: nie tworzy drugiej fizycznej kopii JAR-u, ale nie jest jeszcze końcową migracją artefaktów do magazynu. Przed zastąpieniem symlinków rzeczywistymi pakietami należy wykonać analizę zależności każdego filtra.

OpenXML zawiera wyjątek od przejściowego modelu zależności: `common-io-3.12.0.jar` jest fizycznie dołączony do `filters/openxml/`, ponieważ filtr odwołuje się do klas `com.twelvemonkeys.io.ole2.*`. Zależność jest deklarowana w `filter.json` i walidowana przed uznaniem filtra za używalny. Biblioteka pochodzi z już istniejącego prywatnego runtime Okapi; nie była pobierana ani instalowana globalnie.

Stan migracji na 2026-10-06:
- implementacje filtrów są fizycznie umieszczone w `filters/<nazwa>/` dla: epub, html, json, markdown, openoffice, openxml, xliff, xliff2 i yaml;
- `filter.json` definiuje `name` i `entry_class`, a OpenXML dodatkowo deklaruje `TwelveMonkeys Common IO`;
- część zależności nadal jest symlinkami do `src/tlumacz/resources/okapi-runtime` i jest to stan przejściowy;
- fizycznie w pakietach znajdują się m.in. biblioteki `flexmark*` dla Markdown oraz `common-io-3.12.0.jar` dla OpenXML;
- końcowa migracja zależności do samowystarczalnych pakietów pozostaje w TODO-022j.


STAN PO DOMKNIĘCIU TODO-022j (2026-10-06)

Wszystkie JAR-y w pakietach filtrów są fizycznymi plikami. Nie należy ponownie wprowadzać symlinków do `okapi-runtime` jako mechanizmu dostarczania zależności filtra.

Wspólny `src/tlumacz/resources/okapi-runtime/` zawiera wyłącznie runtime współdzielony. Zależności specyficzne dla filtrów są dostarczane w pakiecie konsumenta. Dotyczy to także `common-io-3.12.0.jar` i `common-lang-3.12.0.jar`, które są wymagane przez obsługę OLE2 w OpenXML.

TODO-022j jest zamknięte. Docelowa migracja magazynu do `~/.config/tlumacz/filters` oraz przyszły loader pakietów użytkownika pozostają osobnymi zadaniami.
