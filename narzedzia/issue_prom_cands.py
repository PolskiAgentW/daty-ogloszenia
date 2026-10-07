"""Cel 7, stage 2: per-act promulgation candidates from the issue dates (tools/issue_dates.py output).

Every act of an issue shares its promulgation date, so the masthead date read for an issue gives:
  - "inna": the act has a promulgation in the API lists of 2026-10-04 that differs from the masthead date,
  - "brak": the act has no promulgation.
An issue is used only if its masthead date is plausible: year = journal year (OCR reads 1930 as 1330, 1982 as 1932) or
the next year for the last issues; "du_rok" readings of 2000+ or with "dnia"/"1936 r." are skipped (they match "z dnia ... r." in the table of
contents or the text, not the masthead "21 grudnia ... Rok 1927"). Before the war MP "warszawa" readings are skipped too (they match "Warszawa, dnia ..." at the end of an act).

Columns: kind, eli, pub, year, volume, api_prom, issue_date, method, quote, first_eli, n_acts, n_same (acts of the issue
whose promulgation equals the masthead date), n_other (with another date), n_brak. Nothing is checked on images here:
"inna" rows are candidates for an image check, not findings.

Usage: python3 tools/issue_prom_cands.py OUT.csv ISSUES.csv [ISSUES.csv ...]"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

LISTS = Path.home() / "ext/eli_lists_20261004"


def plausible(r: dict) -> bool:
    if not r["date"]:
        return False
    y, dy = int(r["year"]), int(r["date"][:4])
    if dy != y and not (dy == y + 1 and r["date"][5:7] == "01"):
        return False
    if "du_rok" in r["method"] and (y >= 2000 or re.search(r"\d{4}\s*r\s*\.|\bdnia\b|~nia\b|\bdr\S?a\b", r["quote"])):
        return False
    if r["pub"] == "MP" and y < 1945 and r["method"].endswith(":warszawa"):
        return False
    return True


def main() -> None:
    out, sources = sys.argv[1], sys.argv[2:]
    acts = defaultdict(list)
    for f in sorted(LISTS.glob("*.json")):
        for i in json.load(f.open(encoding="utf-8"))["items"]:
            acts[(i["publisher"], i["year"], i.get("volume"))].append(i)
    rows, skipped = [], 0
    for src in sources:
        for r in csv.DictReader(open(src, encoding="utf-8")):
            if not plausible(r):
                skipped += bool(r["date"])
                continue
            vol = int(r["volume"]) if r["volume"] not in ("", "None") else None
            items = acts[(r["pub"], int(r["year"]), vol)]
            same = sum(i.get("promulgation") == r["date"] for i in items)
            brak = sum(not i.get("promulgation") for i in items)
            for i in sorted(items, key=lambda i: i["pos"]):
                p = i.get("promulgation") or ""
                if p == r["date"]:
                    continue
                rows.append({"kind": "inna" if p else "brak", "eli": i["ELI"], "pub": r["pub"], "year": r["year"],
                             "volume": r["volume"], "api_prom": p, "issue_date": r["date"], "method": r["method"],
                             "quote": r["quote"], "first_eli": r["first_eli"], "n_acts": len(items), "n_same": same,
                             "n_other": len(items) - same - brak, "n_brak": brak})
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]) if rows else ["kind"])
        w.writeheader()
        w.writerows(rows)
    by = defaultdict(int)
    for r in rows:
        by[(r["kind"], r["pub"], int(r["year"]) // 10 * 10)] += 1
    print(len(rows), "rows;", skipped, "issues with an implausible date skipped")
    for k in sorted(by):
        print(*k, by[k])


if __name__ == "__main__":
    main()
