# Odczyt daty numeru z winiety (Dziennik Ustaw / Monitor Polski, 1918–2011)

Dla każdego numeru dziennika z listy odczytaj z OBRAZU pierwszej strony numeru **datę wydania numeru** (winieta / nagłówek
numeru) i numer dziennika. To kontrola: tę datę porównamy z danymi w API. Lepiej „nieczytelne” niż zgadywanie.

## Lista
Każda linia: `PUB ROK NR PDF` (np. `DU 1938 36 /home/ai/cache/eli/DU/1938/302/text.pdf`). PDF to plik pierwszego aktu
numeru; jego strona 1 powinna być pierwszą stroną numeru (z winietą). Obraz:
`pdftoppm -r 150 -f 1 -l 1 -singlefile -png PDF /tmp/<OUT bez .jsonl>/PUB-ROK-NR` (plik PUB-ROK-NR.png) i obejrzyj PNG
narzędziem Read. Winieta jest na górze strony. Przy drobnym albo wątpliwym druku wytnij SAMĄ linię z datą w większej
rozdzielczości (`pdftoppm -r 300 -x X -y Y -W W -H H`, współrzędne w pikselach przy danym -r); Read zmniejsza obrazy szersze
niż ok. 2000 px, więc pełna szerokość strony przy 300 dpi traci szczegóły.

## Jak wygląda data numeru
- Dz.U. przed wojną: duży tytuł „DZIENNIK USTAW RZECZYPOSPOLITEJ POLSKIEJ”, pod nim po bokach np. „21 grudnia” i „Rok 1927”,
  „Nr 113”; od ok. 1938 r. także układ „Warszawa, dnia 20 maja 1938 r.” i „Nr 36” pod tytułem.
- Dz.U. 1918–1919: „Dziennik Praw Państwa Polskiego”, data obok numeru.
- Dz.U. po wojnie i M.P. po wojnie: pod tytułem „Warszawa, dnia 8 października 1999 r.” i „Nr 83”.
- M.P. przed wojną: linia NAD tytułem „MONITOR POLSKI”: „Nr. 160. Warszawa, Poniedziałek 13 lipca 1936 roku. Rok XIX.”
  („Rok XIX” to rocznik wydawnictwa, nie rok kalendarzowy). Dzień tygodnia wolno użyć tylko do POTWIERDZENIA odczytu; jeśli
  cyfra jest wątpliwa i rozstrzygałby ją dopiero dzień tygodnia, to `readable` = no i opis w `note`.
- „Przedruk.” nad tytułem: egzemplarz przedruku; zapisz datę z jego winiety i `--reprint yes`.
- NIE są datą numeru: daty w spisie treści („Ustawa z dnia …”), data aktu pod jego tytułem, „Warszawa, dnia …” na końcu aktu
  przed podpisem (to data aktu). Data numeru jest w winiecie, na samej górze strony, nad spisem treści / pierwszym aktem.
- Jeśli strona 1 nie ma winiety (PDF zaczyna się w środku numeru), napisz to (`masthead`: false).

## Wynik: jedna linia na numer, dopisywana do OUT skryptem
```
python3 /home/ai/ext/issues/wadd.py OUT --pub DU --year 1938 --nr 36 --masthead yes --date 1938-05-20 --nr-seen 36 \
    --readable yes --reprint no --note "Winieta: „Warszawa, dnia 20 maja 1938 r.” | „Nr 36”"
```
- `--date` (RRRR-MM-DD) tylko gdy dzień, miesiąc i rok daty numeru są czytelne na obrazie; inaczej `--date none --readable no`.
  `--readable` dotyczy daty. `--nr-seen` = numer dziennika widoczny w winiecie (albo none).
- Jeśli numer w winiecie ≠ NR z listy albo rok w winiecie ≠ ROK: zapisz to, co widać, i opisz w `--note`.
- `--note`: dosłownie data z winiety i wątpliwości. W notatce używaj cudzysłowów „…”, nie apostrofów.
- Nie zmieniaj innych plików, nie łącz się z internetem; w /home/ai/ext/issues/ nie listuj katalogów i nie otwieraj nic poza
  tą instrukcją, swoją listą i swoim OUT.

## Pliki robocze
Obrazy i skrypty tylko w /tmp/<nazwa pliku OUT bez .jsonl>/ (np. /tmp/w01/).
