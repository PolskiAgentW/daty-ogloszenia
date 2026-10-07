"""Cel 7, stage 2: order check of masthead dates — within a journal year, issue N+1 is not dated before issue N.

    python3 tools/issue_order_check.py OUT.csv BRAK.csv [BRAK_rest.csv ...] --issues ISSUES.csv [ISSUES.csv ...]

The date of every issue of the brak lists (tools/issue_brak_list.py: issue_date, or in _rest the parser date when
parser = ocr300) is compared with the nearest earlier and later issue of the same journal year that has a date:
the API majority promulgation of that issue (api_majority in tools/issue_dates.py output) or else its brak-list date.
A misread digit (3/8, 1/7) usually breaks the order; an issue out of order is not taken without an image reading.
Second check: no act of the issue may have an announcementDate (date of the act, API lists of 2026-10-04) after the
issue date. Either the masthead was misread or the act date in the API is wrong; the image decides.
Third check: a "Warszawa, dnia …" match (parser method warszawa*) preceded by a lowercase word in the quote may be the
place and date under an act, not the masthead (MP 1947 Nr 50: " Drabarek Warszawa, dnia 15 marca 1947", masthead
18 kwietnia; both tesseract readings took the same line).
Fourth check: an issue number in the quote ("Nr 78", "No 17"; digits split by OCR joined: "Nr 14 7" = 147) that is
not the volume: the page may belong to another issue (MP 1951 Nr 104: the PDF of its first act, 256 pages, starts
with the masthead of Nr A-94) or the OCR misread the number; the image decides.
Writes OUT.csv with the flagged issues (reason, neighbours, the act dated later) and prints counts per basis."""
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

LISTS = Path.home() / "ext/eli_lists_20261004"
NR = re.compile(r"(?:\bNr\.?|№|\bNo\.?|\bN[oO0Q]\b\.?)\s*(?:A\s*[-–—]\s*)?(\d{1,3}(?:[ ']\d{1,2})?)\b")

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("brak", nargs="+")
ap.add_argument("--issues", nargs="+", required=True)
a = ap.parse_args()
known = {}  # (pub, year, volume) -> (date, source)
for fn in a.issues:
    for r in csv.DictReader(open(fn, encoding="utf-8")):
        if r["api_majority"]:
            known[(r["pub"], r["year"], r["volume"])] = (r["api_majority"], "api")
cand = {}
for fn in a.brak:
    for r in csv.DictReader(open(fn, encoding="utf-8")):
        d = r["issue_date"] or (r["parser"] if r["parser"] and r["parser"] == r["ocr300"] else "")
        if d:
            cand[(r["pub"], r["year"], r["volume"])] = (d, r)
by_year = defaultdict(dict)
for k, (d, _) in cand.items():
    by_year[k[:2]][int(k[2])] = (d, "lista")
for k, (d, src) in known.items():
    if k[2].isdigit():
        by_year[k[:2]][int(k[2])] = (d, src)  # the API majority wins over a reading
ann = {i["ELI"]: i.get("announcementDate") or "" for f in sorted(LISTS.glob("*.json"))
       for i in json.load(f.open(encoding="utf-8"))["items"]}
bad, c = [], Counter()
for k, (d, r) in sorted(cand.items()):
    seq = by_year[k[:2]]
    v = int(k[2])
    prev = max((n for n in seq if n < v), default=None)
    nxt = min((n for n in seq if n > v), default=None)
    ordered = (prev is None or seq[prev][0] <= d) and (nxt is None or d <= seq[nxt][0])
    later = [f"{e} {ann[e]}" for e in r["eli_brak"].split() if ann.get(e, "") > d]
    q = r["quote"]
    prose = (r["parser_method"].split(":")[-1].startswith("warszawa")
             and re.search(r"[A-ZĄĆĘŁŃÓŚŹŻ]?[a-ząćęłńóśźż]{3,}", q[:max(0, q.lower().find("arszaw") - 1)]))
    m = NR.search(q)
    other_nr = bool(m) and re.sub(r"\D", "", m[1]) != k[2]
    ok = ordered and not later and not prose and not other_nr
    c[(r["basis"], ok)] += 1
    if not ok:
        bad.append({"pub": k[0], "year": k[1], "volume": k[2], "date": d, "basis": r["basis"],
                    "reason": " + ".join(x for x, y in (("order", not ordered), ("act later", later), ("prose before", prose), ("nr in quote", other_nr)) if y),
                    "act_later": " ".join(later),
                    "prev": f"{prev} {seq[prev][0]} {seq[prev][1]}" if prev is not None else "",
                    "next": f"{nxt} {seq[nxt][0]} {seq[nxt][1]}" if nxt is not None else "",
                    "n_brak": r["n_brak"], "first_eli": r["first_eli"]})
with open(a.out, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, ["pub", "year", "volume", "date", "basis", "reason", "act_later", "prev", "next", "n_brak",
                           "first_eli"])
    w.writeheader()
    w.writerows(bad)
for basis in sorted({b for b, _ in c}):
    print(f"{c[(basis, True)]:5d} ok  {c[(basis, False)]:4d} flagged  {basis}")
