"""Kontrola 2: czy PDF podpięty pod rekord API ELI to ten akt (numer pozycji w druku).

Strona 1 PDF-u (pdftotext, pierwsze 40 niepustych linii): numery z nagłówków „Poz. …” (także „569 i 570”,
„569–571”) i z samodzielnych linii z liczbą (numer aktu nad tytułem w starszych rocznikach).
  ok              pozycja z API jest w nagłówku „Poz.”
  ok-numer        pozycja z API jest tylko jako samodzielna liczba
  bez-numerow     na stronie 1 nie ma żadnego numeru (nie sprawdzone)
  inne-numery     są numery, ale żaden nie jest w odległości ≤ 5 od pozycji z API (nie sprawdzone)
Gdy na stronie 1 są tylko sąsiednie numery (±5), szukane są na wszystkich stronach:
  dalsza-strona   pozycja jest w nagłówku „Poz.” na dalszej stronie (PDF z kilkoma aktami, w porządku)
  numer-dalej     pozycja jest tylko jako samodzielna liczba na dalszej stronie
  KANDYDAT        pozycji nie ma nigdzie w PDF, są numery sąsiednich aktów: PDF może być PDF-em innego aktu.
KANDYDAT trzeba obejrzeć (obraz strony / tekst PDF), opis i zmierzona trafność w README.md. Dla skanów sprzed
1990 r. metoda nie działa (warstwa OCR wydawcy myli numery), więc te lata są pomijane bez --takze-przed-1990.

    python3 zly_pdf.py --pub MP --lata 1990-2026 WYNIK.csv [--procesy 4]"""
import argparse
import csv
import re
import sys
from collections import Counter
from multiprocessing import Pool

from wspolne import cached_acts, pdftext, years

RX_POZ = re.compile(r'(?<![a-ząćęłńóśźż])Poz\.\s*((?:\d[\d ]*\d|\d)(?:\s*(?:,|i|oraz|[-–—])\s*(?:\d[\d ]*\d|\d))*)')
RX_NUM_LINE = re.compile(r'^\s*(\d{1,4})\s*\.?\s*$')


def parse_list(s: str) -> set[int]:
    out = set()
    for p in re.split(r'\s*(,|\bi\b|oraz)\s*', s):
        p = p.strip()
        if not p or p in (',', 'i', 'oraz'):
            continue
        m = re.match(r'^(\d[\d ]*?)\s*[-–—]\s*(\d[\d ]*)$', p)
        if m:
            a, b = int(m.group(1).replace(' ', '')), int(m.group(2).replace(' ', ''))
            out.update(range(a, b + 1) if 0 <= b - a <= 50 else (a, b))
        elif re.match(r'^\d[\d ]*$', p):
            out.add(int(p.replace(' ', '')))
    return out


def numbers(lines) -> tuple[set[int], set[int]]:
    poz, nums = set(), set()
    for ln in lines:
        for m in RX_POZ.finditer(ln):
            poz |= parse_list(m.group(1))
        m = RX_NUM_LINE.match(ln)
        if m:
            nums.add(int(m.group(1)))
    return poz, nums


def check(job):
    meta, pdf = job
    pos = meta.get("pos")
    lines = [ln for ln in pdftext(pdf, 1, 1).splitlines() if ln.strip()]
    poz, nums = numbers(lines[:40])
    pages = ""
    if pos in poz:
        v = "ok"
    elif pos in nums:
        v = "ok-numer"
    elif not poz and not nums:
        v = "bez-numerow"
    elif not any(0 < abs(n - pos) <= 5 for n in poz | nums):
        v = "inne-numery"
    else:
        txt = pdftext(pdf)
        pages = txt.count("\f")
        all_poz, all_nums = numbers(txt.splitlines())
        v = "dalsza-strona" if pos in all_poz else "numer-dalej" if pos in all_nums else "KANDYDAT"
        poz, nums = all_poz, all_nums
    return [meta.get("ELI"), meta.get("volume"), pos, v, " ".join(map(str, sorted(poz)))[:120],
            " ".join(map(str, sorted(nums)))[:120], pages, meta.get("announcementDate"), meta.get("promulgation"),
            (meta.get("title") or "")[:160]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pub", required=True, choices=("DU", "MP"))
    ap.add_argument("--lata", required=True)
    ap.add_argument("wynik")
    ap.add_argument("--procesy", type=int, default=4)
    ap.add_argument("--takze-przed-1990", action="store_true")
    a = ap.parse_args()
    yrs = [y for y in years(a.lata) if y >= 1990 or a.takze_przed_1990]
    jobs = list(cached_acts(a.pub, yrs))
    c = Counter()
    with open(a.wynik, "w", newline="", encoding="utf-8") as fo, Pool(a.procesy) as pool:
        w = csv.writer(fo)
        w.writerow(["eli", "numer_dziennika", "pozycja", "wynik", "poz_w_pdf", "liczby_w_pdf", "stron",
                    "announcementDate", "promulgation", "tytul"])
        for r in pool.imap(check, jobs, chunksize=16):
            w.writerow(r)
            c[r[3]] += 1
    print(a.pub, len(jobs), "PDF:", dict(c), file=sys.stderr)


if __name__ == "__main__":
    main()
