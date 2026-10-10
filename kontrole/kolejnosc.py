"""Kontrola 7: promulgation poza kolejnością pozycji (same listy roczników, bez PDF-ów; od 2012 r.).

Od 2012 r. pozycje Dz.U. i M.P. dostają numery w kolejności ogłaszania, więc promulgation rośnie razem z pozycją.
Kandydat: promulgation późniejsza niż któraś z --okno następnych pozycji albo wcześniejsza niż któraś z --okno
poprzednich, albo pusta. Kandydatami są też sąsiedzi złej daty, więc o tym, która data jest zła, rozstrzyga dopiero
nagłówek PDF-u („Warszawa, dnia …”, naglowek_2012.py) albo druk.
Kontrola nie widzi złej daty, która nie łamie kolejności (np. cały blok pozycji o dzień za wcześnie), dlatego
po potwierdzeniu warto sprawdzić sąsiednie pozycje z tą samą datą w API.

    python3 kolejnosc.py WYNIK.csv [--pub DU MP] [--lata 2012-2026] [--okno 3]"""
import argparse
import csv
import datetime as dt

from wspolne import list_items, years


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("wynik")
    ap.add_argument("--pub", nargs="+", default=["DU", "MP"])
    ap.add_argument("--lata", default=f"2012-{dt.date.today().year}")
    ap.add_argument("--okno", type=int, default=3)
    a = ap.parse_args()
    k = a.okno
    rows, n = [], 0
    for pub in a.pub:
        for y in years(a.lata):
            items = sorted(list_items(pub, y), key=lambda i: i["pos"])
            n += len(items)
            for i, it in enumerate(items):
                p = it.get("promulgation") or ""
                prev = [x["promulgation"] for x in items[max(0, i - k):i] if x.get("promulgation")]
                nxt = [x["promulgation"] for x in items[i + 1:i + 1 + k] if x.get("promulgation")]
                if not p:
                    why = "brak promulgation"
                elif nxt and p > min(nxt):
                    why = f"późniejsza niż następne ({min(nxt)})"
                elif prev and p < max(prev):
                    why = f"wcześniejsza niż poprzednie ({max(prev)})"
                else:
                    continue
                rows.append([it["ELI"], p, why, " ".join(prev), " ".join(nxt), (it.get("title") or "")[:160]])
    with open(a.wynik, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["eli", "promulgation", "uwaga", "poprzednie", "nastepne", "tytul"])
        w.writerows(rows)
    print(n, "aktów, kandydaci:", len(rows))


if __name__ == "__main__":
    main()
