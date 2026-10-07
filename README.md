# Daty ogłoszenia aktów z winiet numerów (Dz.U. i M.P. 1918–2011)

Data ogłoszenia aktów **Dziennika Ustaw** i **Monitora Polskiego**, dla których API ELI Sejmu
(`api.sejm.gov.pl/eli`) jej nie podaje (puste pole `promulgation`), odczytana z winiety numeru dziennika
w PDF-ach z tego API.
*Promulgation dates of Polish Journal of Laws and Monitor Polski acts that the Sejm ELI API lacks, read from the
masthead of each journal issue in the API's own PDFs.*

> **Nieoficjalne.** Daty odczytano automatycznie i z obrazów stron. Odczyt może być błędny (pomiar niżej).
> Wiążący jest druk: PDF aktu w API ELI.

## Pliki

- [`akty.csv`](akty.csv): jeden wiersz na akt: `eli`, `dziennik` (DU/MP), `rok`, `numer`, `pozycja`,
  `data_ogloszenia` (RRRR-MM-DD), `odczyty` (z czego wzięto datę, niżej).
- [`numery.csv`](numery.csv): jeden wiersz na numer dziennika: `dziennik`, `rok`, `numer`, `data_ogloszenia`,
  `odczyty`, `akt_z_winieta` (ELI aktu, którego PDF zaczyna się od winiety numeru), `aktow_w_numerze`,
  `aktow_bez_daty_w_api`, `akty_bez_daty_w_api` (ELI rozdzielone spacją).
- [`odczyty/numery_odczyty.csv`](odczyty/numery_odczyty.csv): wszystkie odczyty każdego numeru z aktami bez daty
  w API, także numerów pominiętych (kolumna `basis` podaje powód): `parser` (warstwa tekstowa albo tesseract 200 dpi,
  sposób w `parser_method`, fragment tekstu w `quote`), `ocr300`, `image` (odczyty z obrazu).
- [`odczyty/obraz.jsonl`](odczyty/obraz.jsonl): każdy odczyt z obrazu strony z opisem (`note`: co jest w winiecie,
  wątpliwości).
- [`narzedzia/`](narzedzia/): skrypty, którymi to zrobiono (kod roboczy, ze ścieżkami lokalnymi) i instrukcja
  odczytu z obrazu.

Stan list API ELI: 2026-10-07 (listy roczników `api.sejm.gov.pl/eli/acts/DU/<rok>` i `…/MP/<rok>`). Akty, które API ma już z datą ogłoszenia, nie są tu powtarzane.

## Skąd data

Wszystkie akty jednego numeru dziennika mają tę samą datę ogłoszenia: datę wydania numeru. Jest ona wydrukowana
w winiecie na pierwszej stronie numeru, np. „Warszawa, dnia 8 października 1952 r.” pod tytułem dziennika albo
„Nr. 160. Warszawa, Poniedziałek 13 lipca 1936 roku” nad tytułem Monitora Polskiego. Pierwsza strona PDF-u
pierwszej pozycji numeru w API ELI to zwykle właśnie ta strona.

Każda data ma co najmniej dwa zgodne odczyty tej winiety:

| `odczyty` | odczyt 1 | odczyt 2 |
|---|---|---|
| `warstwa tekstowa PDF + tesseract 300 dpi` | tekst ukryty w PDF (OCR wydawcy) | tesseract 300 dpi z obrazu strony |
| `tesseract 200 dpi + tesseract 300 dpi` | tesseract 200 dpi (PDF bez warstwy tekstu albo bez daty w niej) | tesseract 300 dpi |
| `obraz strony + …` | odczyt z obrazu strony (model AI z obsługą obrazów, wycinek powiększony przy drobnym druku) | jeden z odczytów wyżej |
| `obraz strony ×2` | odczyt z obrazu strony | drugi, niezależny odczyt z obrazu (inny model) |

Dopisek `trzeci odczyt inny` znaczy, że trzeci odczyt (zwykle OCR) dał inną datę, a odczyt z obrazu zgodny z jednym
z pozostałych rozstrzygnął. Dopisek `odczyty maszynowe inne` znaczy, że oba odczyty z obrazu dały tę samą datę,
a odczyty maszynowe inną (np. zatarta cyfra albo data spod aktu zamiast winiety).

Numer nie trafia tu bez odczytu z obrazu, gdy:
- jego data jest wcześniejsza niż data poprzedniego numeru albo późniejsza niż następnego (w tym samym roczniku),
- któryś z jego aktów ma w API datę wydania (`announcementDate`) późniejszą niż data numeru,
- dopasowana data „Warszawa, dnia …” stoi po zwykłym tekście, więc może być datą pod aktem, a nie winietą,
- numer dziennika odczytany obok daty różni się od numeru w API.

Odczyt z obrazu liczy się tylko wtedy, gdy numer w winiecie jest ten sam co w API, rok daty to rok dziennika (albo
styczeń następnego) i strona nie jest przedrukiem. Pominięte są też akty, które mają w API datę wydania późniejszą niż
data numeru: wtedy nie wiadomo, czy błędna jest data aktu, czy jego numer dziennika w API.

## Jak dokładne

- **Próba losowa:** 120 numerów wylosowanych z tych, w których dwa odczyty maszynowe dały tę samą datę
  (60 z 4 667 numerów „warstwa tekstowa PDF + tesseract 300 dpi”, 60 z 1 917 „tesseract 200 dpi + tesseract 300 dpi”),
  przeczytano z obrazu strony. Obraz potwierdził datę we wszystkich 120. To nie znaczy, że błędów nie ma: przy takiej
  próbie odsetek błędnych dat w tej grupie jest z 95-procentową pewnością mniejszy niż ok. 2,5%.
- **Kontrole:** cztery reguły z sekcji wyżej oznaczyły 88 numerów z dwoma zgodnymi odczytami maszynowymi. Obraz
  strony potwierdził datę w 82, w 3 oba odczyty maszynowe były błędne w ten sam sposób (np. M.P. 1947 Nr 50: oba
  wzięły datę spod aktu „Warszawa, dnia 15 marca 1947”, a winieta ma „18 kwietnia 1947 roku”), 3 zostały
  nierozstrzygnięte i ich tu nie ma.
- **Dwa odczyty z obrazu:** 325 numerów przeczytano z obrazu dwa razy, niezależnie, dwoma różnymi
  modelami. Daty zgadzają się we wszystkich 325. Dwa odczyty tej samej strony nie wykryją jednak strony z innego
  numeru, dlatego liczy się tylko odczyt, w którym numer i rok winiety zgadzają się z API.
- **Kontrola z zewnątrz:** 10 aktów z tej listy dostało datę ogłoszenia w API między 4 a 7 października 2026 r.
  We wszystkich 10 jest ona taka sama jak odczytana tutaj (tych aktów już tu nie ma).
- Daty, w których odczyty się różnią albo jest tylko jeden odczyt, nie trafiły tu.

Mimo to pomyłka jest możliwa. Jeśli data nie zgadza się z drukiem, zgłoś to w Issues (ELI aktu i data z PDF).

## Pokrycie

Akty Dz.U. i M.P. z lat 1918–2011 bez daty ogłoszenia w API (listy z 2026-10-07) i ile z nich ma datę tutaj:

| lata | Dz.U.: bez daty w API | Dz.U.: data tutaj | M.P.: bez daty w API | M.P.: data tutaj |
|---|---:|---:|---:|---:|
| 1910–1919 | 438 | 244 | 0 | 0 |
| 1920–1929 | 8 703 | 7 644 | 0 | 0 |
| 1930–1939 | 153 | 153 | 40 | 36 |
| 1940–1949 | 2 296 | 2 170 | 3 434 | 2 860 |
| 1950–1959 | 3 596 | 3 498 | 12 921 | 12 135 |
| 1960–1969 | 3 266 | 3 146 | 4 118 | 4 036 |
| 1970–1979 | 418 | 387 | 2 623 | 2 597 |
| 1980–1989 | 6 | 6 | 2 917 | 2 795 |
| 1990–1999 | 5 958 | 5 767 | 5 951 | 5 394 |
| 2000–2009 | 1 061 | 417 | 1 482 | 594 |
| razem | 25 895 | 23 432 | 33 486 | 30 447 |

Razem 53 879 z 59 381 aktów (90,7%) w 7 283 numerach.

Czego tu nie ma, choć API nie ma daty:
- numerów, których winiety nie ma na pierwszej stronie PDF-u żadnego aktu: w Dz.U. 2000 i M.P. 2000–2001 PDF-y są
  cięte na pojedyncze akty, a strona winiety i spisu treści nie należy do żadnego z nich; podobnie Dz.U. 1921
  i M.P. 1950–1952 (część numerów),
- numerów, w których pierwsza strona PDF-u pokazuje winietę innego numeru albo rocznika,
- winiet nieczytelnych (zatarta cyfra dnia lub roku),
- numerów z jednym odczytem albo z odczytami różnymi,
- aktów z ELI spoza zwykłej postaci (np. `MP/1946/0910170`), których PDF-ów nie pobierano.

## Licencja

Akty normatywne i urzędowe dokumenty nie są przedmiotem prawa autorskiego (art. 4 ustawy o prawie autorskim
i prawach pokrewnych). Pliki tego repozytorium: CC0 1.0.
