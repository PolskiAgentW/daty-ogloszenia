"""Kontrola 1: daty w listach roczników API ELI (bez PDF-ów).

Dla każdego aktu:
  announcementDate               ≠ pierwsza data „z dnia D miesiąca RRRR” w tytule,
  announcementDate>promulgation  data aktu późniejsza niż data ogłoszenia,
  promulgation                   data ogłoszenia spoza roku dziennika albo z przyszłości.
Umowy międzynarodowe są pomijane (API podaje przy nich zwykle datę ratyfikacji, a tytuł datę umowy).
Wynik to kandydaci: która data jest dobra, rozstrzyga dopiero druk (PDF aktu, winieta numeru), opis w README.md.

    python3 daty_tytul.py WYNIK.csv [--pub DU MP] [--lata 1918-2026] [--listy KATALOG] [--pomin ZGLOSZONE.csv]

--listy: katalog z listami (*.json z polem items), zamiast ELI_CACHE/<PUB>/<rok>.json.
--pomin: CSV z kolumnami eli, pole; te pary nie trafią do wyniku (np. już zgłoszone)."""
import argparse
import csv
import datetime as dt
import json
import re
from pathlib import Path

from wspolne import MONTH_PATS, iso, list_items, years

DATE_RE = re.compile(r"z\s+dnia\s+(\d{1,2})\s+(" + "|".join(MONTH_PATS) + r")\s+(\d{4})", re.I)
TREATY = re.compile(r"(Umowa|Konwencja|Protokół|Porozumienie)\b")


def items(a):
    if a.listy:
        for f in sorted(Path(a.listy).glob("*.json")):
            yield from json.loads(f.read_text(encoding="utf-8"))["items"]
        return
    for pub in a.pub:
        for y in years(a.lata):
            yield from list_items(pub, y)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("wynik")
    ap.add_argument("--pub", nargs="+", default=["DU", "MP"])
    ap.add_argument("--lata", default=f"1918-{dt.date.today().year}")
    ap.add_argument("--listy")
    ap.add_argument("--pomin")
    a = ap.parse_args()
    today = dt.date.today().isoformat()
    skip = set()
    if a.pomin:
        skip = {(r["eli"], r["pole"]) for r in csv.DictReader(open(a.pomin, encoding="utf-8"))}
    rows, n = [], {"aktow": 0, "umowy": 0, "bez_daty_w_tytule": 0, "pominiete": 0}
    for act in items(a):
        n["aktow"] += 1
        eli, title = act["ELI"], act.get("title") or ""
        if (act.get("type") or "").startswith("Umowa") or TREATY.match(title):
            n["umowy"] += 1
            continue
        ann, prom = act.get("announcementDate"), act.get("promulgation")
        found = []
        m = DATE_RE.search(title)
        if m:
            d = iso(m[1], m[2], m[3])
            if ann and ann != d:
                found.append(("announcementDate", ann, d, "tytuł: " + m[0]))
        else:
            n["bez_daty_w_tytule"] += 1
        if ann and prom and ann > prom:
            found.append(("announcementDate>promulgation", ann, prom, ""))
        if prom and (prom[:4] != str(act["year"]) or prom > today):
            found.append(("promulgation", prom, "", f"rok dziennika {act['year']}"))
        for pole, val, exp, note in found:
            if (eli, pole.split(">")[0]) in skip:
                n["pominiete"] += 1
                continue
            rows.append({"eli": eli, "typ": act.get("type"), "pole": pole, "wartosc_w_API": val, "oczekiwana": exp,
                         "uwaga": note, "announcementDate": ann, "promulgation": prom, "tytul": title[:200]})
    with open(a.wynik, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["eli", "typ", "pole", "wartosc_w_API", "oczekiwana", "uwaga",
                                           "announcementDate", "promulgation", "tytul"])
        w.writeheader()
        w.writerows(rows)
    print(n, "kandydaci:", len(rows))


if __name__ == "__main__":
    main()
