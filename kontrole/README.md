# Kontrole metadanych API ELI względem druku

Skrypty, które porównują dane aktów Dziennika Ustaw i Monitora Polskiego w API ELI Sejmu (`api.sejm.gov.pl/eli`)
z PDF-ami tych aktów z tego samego API, oraz zmierzona trafność każdej kontroli.
*Scripts that compare the metadata of Polish Journal of Laws and Monitor Polski acts in the Sejm ELI API with the
acts' own PDFs from that API, with the measured precision of each check.*

Wynik każdej kontroli to **kandydaci**, nie stwierdzone niezgodności. O tym, która wartość jest dobra, rozstrzyga druk:
tekst albo obraz strony PDF-u. Kontrole wskazują tylko, gdzie patrzeć. Tabela niżej pokazuje, jaka część kandydatów
okazała się prawdziwa, gdy ich obejrzano.

Wymagania: Python 3.10+, `pdftotext` (poppler-utils), bez dodatkowych pakietów.

## Kolejność

```sh
cd kontrole
python3 pobierz.py listy DU 1918-2026 && python3 pobierz.py listy MP 1918-2026  # listy roczników, ok. 220 zapytań
python3 daty_tytul.py wynik_daty.csv                                         # kontrola 1, same listy
python3 pobierz.py pdf MP 2012-2026                                          # rekordy + PDF-y (długo, niżej)
python3 zly_pdf.py --pub MP --lata 2012-2026 wynik_zly_pdf.csv               # kontrola 2
python3 numer_tytulu.py --pub MP --lata 2012-2026 wynik_numer.csv            # kontrola 3
python3 metadane.py --pub MP --lata 2012-2026 wynik_metadane.csv             # kontrola 4
python3 naglowek_2012.py --pub MP --lata 2012-2026 wynik_naglowek.csv        # kontrola 5
python3 zmiany_api.py zgloszone.csv                                          # czy API już ma wartość z druku
```

Dane trafiają do katalogu `ELI_CACHE` (domyślnie `~/cache/eli`, ten sam układ co w
[eli2md](https://github.com/PolskiAgentW/eli2md)). `pobierz.py` wysyła jedno zapytanie naraz z przerwą 1 s, więc cały
Dz.U. i M.P. (ok. 165 tys. aktów, dwa pliki na akt) to kilka dni pobierania. Pobieranie można przerwać i wznowić.
Kontrole 2–5 nie korzystają z sieci.

## Kontrole

| skrypt | co porównuje | wynik do obejrzenia |
|---|---|---|
| `daty_tytul.py` | `announcementDate` (data aktu) z datą „z dnia …” w tytule; `announcementDate` późniejszą niż `promulgation`; `promulgation` spoza roku dziennika | każdy wiersz |
| `zly_pdf.py` | pozycję z API z numerami „Poz. …” i numerami aktów w PDF-ie | `KANDYDAT`: w PDF-ie są numery sąsiednich pozycji, a tej nie ma nigdzie |
| `numer_tytulu.py` | numer z tytułu („nr 110-15-2008”, „Nr 59”) z tekstem PDF-u | `BRAK` |
| `metadane.py` | datę i numer z tytułu z nagłówkiem aktu w PDF-ie (pod „Poz. N”) | `DATA`, `NR`, `DATA+NR` |
| `naglowek_2012.py` | `promulgation` z datą „Warszawa, dnia …” w nagłówku dziennika na stronie 1 PDF-u (od 2012 r.) | `INNA`, `BRAK_W_API` |
| `zmiany_api.py` | listę zgłoszonych wartości ze stanem API teraz | – |

Szczegóły każdej kontroli są w nagłówku skryptu.

## Zmierzona trafność

Liczby z kontroli przeprowadzonych 4–7 października 2026 r. na listach i PDF-ach z API z tych dni. „Potwierdzone” znaczy:
druk (tekst PDF-u, a dla skanów obraz strony) zgadza się z wnioskiem kontroli. Przy datach sprzed 2000 r. były to dwa
niezależne odczyty obrazu strony i za potwierdzone uznano tylko daty, w których oba dały ten sam wynik.

| kontrola | zakres | kandydaci | potwierdzone | fałszywe albo nierozstrzygnięte |
|---|---|---:|---:|---|
| `daty_tytul.py`, data aktu | akty od 2000 r. | 562 | 555 (490: `announcementDate` inna niż druk, 65: data w tytule inna niż druk) | 7: w druku brak daty aktu |
| `daty_tytul.py`, data aktu | akty sprzed 2000 r., czytane z obrazu | 479 | 298 (195: `announcementDate`, 103: tytuł) | 121: API zgodne z drukiem (data w tytule to nie data tego aktu albo API już zmienione); 54: odczyt niepewny albo bez daty; 6: druk niejednoznaczny |
| `zly_pdf.py` | 1990–2026: 68 822 PDF-y (M.P. całe, Dz.U. 1990–2011 i 2025–2026 prawie całe, Dz.U. 2012–2024 w małej części) | 10 | 9 | 1: warstwa OCR skanu odczytała „61” jako „81” |
| `zly_pdf.py` | skany sprzed 1990 r. | 414 | 0 z 4 obejrzanych | warstwa OCR wydawcy myli numery pozycji, dlatego skrypt pomija te lata |
| `numer_tytulu.py` | M.P. 1990–2026 (z lat 1990–1999 tylko część PDF-ów): 8 267 tytułów z numerem | 52 | 43 (w tym 2: PDF innego aktu) | 9: inny zapis numeru w druku albo akt dalej na stronie |
| `numer_tytulu.py` | M.P. 1990–1999, ponownie, wszystkie PDF-y: 226 tytułów | 1 | 0 | 1: warstwa OCR ma „Nr 69”, druk „Nr 59” |
| `numer_tytulu.py` | Dz.U. 1990–2026: 155 tytułów | 0 | – | – |
| `metadane.py` | M.P. 2012–2026, Dz.U. 2025–2026 i część 2024 (razem 21 595 PDF-ów) | 67 | 62 | 5: inny zapis numeru, sygnatura wyroku albo cytowany wyrok w nagłówku |
| `naglowek_2012.py` | M.P. 2012–2026, Dz.U. 2025–2026 i część 2024 (21 595 PDF-ów) | 186 `INNA`, 3 `BRAK_W_API` | nie mierzone (niżej) | – |

Uwagi:
- `daty_tytul.py` porównuje dwa pola tego samego rekordu, więc przy różnicy jedno z nich nie zgadza się z drukiem.
  Nie wiadomo jednak które, dopóki nie obejrzy się druku. Przed 2000 r. co czwarty kandydat okazał się zgodny
  z drukiem: pierwsza data w tytule bywa datą innego aktu (np. aktu zmienianego) albo API zdążyło się zmienić.
- `zly_pdf.py` sprawdza dalej tylko PDF-y, w których na stronie 1 są numery w odległości do 5 od pozycji z API. Jeden
  z 10 potwierdzonych PDF-ów innego aktu (strona 1 pokazywała pozycję o 6 dalej) dostał wynik `inne-numery`
  i znalazł go dopiero `numer_tytulu.py`. Wyniki `inne-numery` i `bez-numerow` nie są więc sprawdzone.
- `metadane.py` dla 2000–2011 nie działa: jeden PDF obejmuje kilka aktów, a warstwa tekstowa części roczników ma
  inne kodowanie polskich liter (np. „paêdziernika”).
- `naglowek_2012.py`: PDF-y od 2012 r. są cyfrowe, więc data w nagłówku pochodzi z tekstu, nie z OCR. 124 ze 186 różnic
  to jeden dzień. Nie wiem, czy to niezgodność, czy inna konwencja (np. data podpisania numeru). Trafności tej kontroli
  nie mierzono na obrazach.
- Zakres to PDF-y, które miałem pobrane. Dz.U. 2012–2024 (akty, które API daje też jako HTML) prawie nie były
  sprawdzane.

## Zmiany w API po zgłoszeniu

Niezgodności potwierdzone w druku przesłano Ośrodkowi Informatyki Kancelarii Sejmu (ISAP) w siedmiu listach: pięć
w formacie `zmiany_api.py`, dwie w innym. Stan API sprawdzony `zmiany_api.py` 9 października 2026 r. (10:36–10:48):

| lista | co zawierała | wiersze | API ma teraz wartość z druku | zmienione na inną wartość | bez zmian |
|---|---|---:|---:|---:|---:|
| 30.09.2026 | `announcementDate` z innym rokiem niż data w tytule i w druku | 6 | 6 | 0 | 0 |
| 01.10.2026 | `announcementDate` i `promulgation` inne niż w druku | 128 | 126 | 2 | 0 |
| 04.10.2026 | akty od 2000 r.: `announcementDate`, data w tytule, `promulgation` inne niż w druku | 566 | 334 | 4 | 228 |
| 07.10.2026 | akty 1918–1999: `announcementDate`, data w tytule, `promulgation` inne niż w druku | 344 | 0 | 0 | 344 |
| 08.10.2026 | `promulgation` inna niż data ogłoszenia w druku (1918–2011 z winiety numeru, od 2012 r. z nagłówka PDF) | 277 | 0 | 0 | 277 |
| razem | | 1 321 | 466 | 6 | 849 |

Dwie listy w innym formacie, sprawdzone osobno 9.10: 11 rekordów z PDF-em innego aktu (07.10): każdy PDF w API
jest ten sam co przed zgłoszeniem (SHA-256); 48 rekordów z innym numerem albo datą aktu w tytule niż w druku (08.10):
0 zmienionych.

Z 6 wierszy „zmienione na inną wartość” 2 to umowy międzynarodowe: API ma teraz datę ratyfikacji, która też jest
w druku (zgłoszenie podawało datę podpisania). W pozostałych 4 nowej wartości w druku nie znalazłem.

Zmiany z listy 04.10 pojawiały się w API stopniowo od 6 października, więc wiersze „bez zmian” to stan na 9.10,
a nie wynik końcowy. Samych list tu nie ma. Pomiar da się powtórzyć na dowolnej własnej liście w formacie opisanym
w nagłówku `zmiany_api.py`.

## Licencja

Kod: CC0 1.0, jak całe repozytorium.
