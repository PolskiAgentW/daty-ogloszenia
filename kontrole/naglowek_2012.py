"""Kontrola 5 (roczniki od 2012): data ogłoszenia (promulgation) w API ELI wobec daty w nagłówku PDF-u aktu.

Od 2012 r. każdy akt ma osobny PDF, a jego strona 1 zaczyna się nagłówkiem dziennika: „DZIENNIK USTAW
RZECZYPOSPOLITEJ POLSKIEJ / Warszawa, dnia 8 października 2025 r. / Poz. 1234”. Brana jest data „Warszawa, dnia …”
z 10 linii od tytułu dziennika (dalsza „Warszawa, dnia” należy już do aktu).
  rowne          promulgation = data z nagłówka
  INNA           różne daty
  BRAK_W_API     API nie ma promulgation, nagłówek ma datę
  poz-inna       „Poz.” w nagłówku ≠ pozycja z API (wtedy daty nie porównuje się; zobacz zly_pdf.py)
  bez-naglowka   nie znaleziono daty w nagłówku

    python3 naglowek_2012.py --pub DU MP --lata 2012-2026 WYNIK.csv [--procesy 4]"""
import argparse
import csv
import re
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

from wspolne import MONTH_PATS, cached_acts, iso, pdftext, years

HEAD = re.compile(r"Warszawa,\s+dnia\s+(\d{1,2})\s+(" + "|".join(MONTH_PATS) + r")\s+(\d{4})", re.I)
POS = re.compile(r"^\s*Poz\.\s*(\d+)\s*$", re.M)


def read(job) -> list:
    meta, pdf = job
    lines = [ln for ln in pdftext(pdf, last=1, layout=True).splitlines()[:40] if ln.strip()]
    t = next((i for i, ln in enumerate(lines) if re.search(r"DZIENNIK\s+USTAW|MONITOR\s+POLSKI", ln)), None)
    head = "\n".join(lines[t:t + 10]) if t is not None else ""
    m, pm = HEAD.search(head), POS.search(head)
    date = iso(m[1], m[2], m[3]) if m else ""
    api = meta.get("promulgation") or ""
    v = ("bez-naglowka" if not date else "poz-inna" if pm and int(pm[1]) != meta["pos"] else
         "BRAK_W_API" if not api else "rowne" if api == date else "INNA")
    return [meta["ELI"], api, date, pm[1] if pm else "", re.sub(r"\s+", " ", m[0]) if m else "", v]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pub", nargs="+", default=["DU", "MP"])
    ap.add_argument("--lata", required=True)
    ap.add_argument("wynik")
    ap.add_argument("--procesy", type=int, default=4)
    a = ap.parse_args()
    jobs = [j for pub in a.pub for j in cached_acts(pub, [y for y in years(a.lata) if y >= 2012])]
    with ProcessPoolExecutor(a.procesy) as ex:
        rows = list(ex.map(read, jobs, chunksize=50))
    with open(a.wynik, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["eli", "promulgation", "data_w_naglowku", "poz_w_naglowku", "cytat", "wynik"])
        w.writerows(rows)
    print(len(rows), "PDF:", dict(Counter(r[-1] for r in rows)), file=sys.stderr)


if __name__ == "__main__":
    main()
