"""Kontrola 3: czy numer z tytułu w API ELI („nr 1130.51.2019”, „nr rej. 686/2025”, „Nr 118”) jest w PDF-ie aktu.

Szuka numeru w całym tekście PDF (pdftotext, bez białych znaków, myślniki ujednolicone).
  jest        numer jest w tekście
  BRAK        numeru nie ma: PDF może być PDF-em innego aktu albo tytuł może mieć numer innego aktu
  bez-tekstu  PDF bez warstwy tekstowej (nie sprawdzone)
BRAK trzeba obejrzeć: częste fałszywe trafienia to inny zapis numeru w druku („1131-2407” wobec „1131-24-07”), błąd
warstwy OCR w skanach („Nr 69” zamiast „Nr 59”) i akt dalej na stronie. Opis i zmierzona trafność w README.md.

    python3 numer_tytulu.py --pub MP --lata 1990-2026 WYNIK.csv [--procesy 3]"""
import argparse
import csv
import re
import sys
from collections import Counter
from multiprocessing import Pool

from wspolne import cached_acts, pdftext, years

RX_NR = re.compile(r'\b[Nn]r\s+(?:rej\.\s*)?([0-9][0-9A-Za-z./\-]*[0-9A-Za-z]|[0-9])')


def norm(s: str) -> str:
    return re.sub(r'\s+', '', s).replace('–', '-').replace('—', '-')


def check(job):
    meta, pdf = job
    title = meta.get("title") or ""
    nr = RX_NR.search(title).group(1).rstrip(".")
    txt = pdftext(pdf)
    v = "bez-tekstu" if not txt.strip() else "jest" if norm(nr) in norm(txt) else "BRAK"
    return [meta.get("ELI"), nr, v, meta.get("announcementDate"), title[:160]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pub", required=True, choices=("DU", "MP"))
    ap.add_argument("--lata", required=True)
    ap.add_argument("wynik")
    ap.add_argument("--procesy", type=int, default=3)
    a = ap.parse_args()
    jobs = [(m, p) for m, p in cached_acts(a.pub, years(a.lata)) if RX_NR.search(m.get("title") or "")]
    c = Counter()
    with open(a.wynik, "w", newline="", encoding="utf-8") as fo, Pool(a.procesy) as pool:
        w = csv.writer(fo)
        w.writerow(["eli", "nr", "wynik", "announcementDate", "tytul"])
        for r in pool.imap(check, jobs, chunksize=8):
            w.writerow(r)
            c[r[2]] += 1
    print(a.pub, len(jobs), "tytułów z numerem:", dict(c), file=sys.stderr)


if __name__ == "__main__":
    main()
