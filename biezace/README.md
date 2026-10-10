# Kontrola bieżących rekordów API ELI

Codziennie (GitHub Actions, [`biezace.yml`](../.github/workflows/biezace.yml), ok. 06:41 UTC) akty Dziennika Ustaw
i Monitora Polskiego, których `promulgation` albo `announcementDate` w API ELI przypada w ostatnich 90 dniach, przechodzą
przez kontrole 1–5 z katalogu [`kontrole`](../kontrole/README.md) (skrypt [`biezace.py`](../kontrole/biezace.py)).
*Daily check of Journal of Laws and Monitor Polski records from the last 90 days in the Sejm ELI API against the acts'
own PDFs; the result is a list of candidates, not confirmed discrepancies.*

- [`kandydaci.csv`](kandydaci.csv): stan na dzień przebiegu. Gdy API dostanie wartość zgodną z drukiem, wiersz znika
  przy następnym przebiegu.
- [`stan.json`](stan.json): data przebiegu, początek okna, liczba sprawdzonych aktów i kandydatów, najnowsza
  `promulgation` w listach. Plik zmienia się codziennie, więc data ostatniego commita pokazuje, czy kontrola działa.
  Gdy najnowszy akt w listach jest starszy niż 10 dni, przebieg kończy się błędem.

Wiersz to **kandydat**: miejsce, w którym rekord API różni się od innego źródła. Która wartość jest dobra, rozstrzyga
druk (PDF aktu). Lista nie jest nigdzie wysyłana.

## Kolumny `kandydaci.csv`

| kolumna | znaczenie |
|---|---|
| `eli` | adres aktu w API, np. `DU/2026/1258` (`https://api.sejm.gov.pl/eli/acts/DU/2026/1258`) |
| `kontrola` | skrypt, który wskazał różnicę (opis w [`kontrole/README.md`](../kontrole/README.md)) |
| `pole` | `announcementDate`, `announcementDate>promulgation`, `promulgation`, `data w tytule`, `numer w tytule`, `PDF` |
| `w_API` | wartość w API w dniu przebiegu |
| `inna_wartosc` | wartość z drugiego źródła (pusta, gdy kontrola wykrywa tylko brak, np. numeru w PDF-ie) |
| `zrodlo_innej_wartosci` | skąd jest `inna_wartosc` (tytuł w API, nagłówek PDF-u z cytatem, numery pozycji w PDF-ie) |
| `od` | pierwszy dzień, w którym kontrola wskazała ten wiersz (pierwszy przebieg: 10.10.2026) |
| `tytul` | tytuł aktu w API (do 200 znaków) |

## Trafność

Pierwszy przebieg, 10.10.2026 (686 aktów z okna 12.07–10.10.2026; lokalnie i w GitHub Actions ten sam wynik):
10 wierszy w 7 aktach. Wszystkie sprawdziłem w tekście PDF-ów. W każdym z 10 wierszy API różni się od druku: w 8 druk
ma `inna_wartosc` (przy 6 wierszach `promulgation` tę samą datę podawała 10.10 także strona aktu u wydawcy,
dziennikustaw.gov.pl albo monitorpolski.gov.pl), w 1 numeru z tytułu nie ma w PDF-ie, a w 1
(`announcementDate>promulgation`) druk ma `announcementDate` z API, ale `promulgation` inną niż API. To mała próbka.
Trafność kontroli na większych zbiorach jest w [`kontrole/README.md`](../kontrole/README.md#zmierzona-trafność).

Różnica `promulgation` o jeden dzień to najczęstszy przypadek. Do 10.10.2026 nie wiedziałem, czy to niezgodność, czy
inna konwencja. Strona aktu u wydawcy podaje jednak tę samą datę co nagłówek PDF-u (liczby w `kontrole/README.md`).
Kontrola codzienna stron wydawcy nie odpytuje, bo ich robots.txt zabrania automatów.

## Obciążenie API

Tylko API ELI, jedno zapytanie naraz, przerwa 1 s. Każdy przebieg pobiera listy roczników (2 zapytania, na początku
roku 4) i PDF-y aktów nowych albo zmienionych od poprzedniego przebiegu (pole `changeDate` w liście). PDF-y
z poprzednich przebiegów są w cache GitHub Actions. Pierwszy przebieg (cały 90-dniowy zbiór PDF-ów) pobiera najwyżej
40 minut, resztę dobierają następne.
