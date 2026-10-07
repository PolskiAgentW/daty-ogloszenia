"""Cel 7: coverage table for the public dates repo (markdown) — acts without promulgation in the API lists of
2026-10-04 vs acts with a masthead date in akty.csv (tools/dates_export.py), per journal and decade.

    python3 tools/dates_stats.py akty.csv [LISTDIR]   (default: the lists of 2026-10-04)"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

LISTS = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.home() / "ext/eli_lists_20261004"
missing, done = Counter(), Counter()
for f in sorted(LISTS.glob("*.json")):
    for i in json.load(f.open(encoding="utf-8"))["items"]:
        if not i.get("promulgation"):
            missing[(i["publisher"], i["year"] // 10 * 10)] += 1
for r in csv.DictReader(open(sys.argv[1], encoding="utf-8")):
    done[(r["dziennik"], int(r["rok"]) // 10 * 10)] += 1
print("| lata | Dz.U.: bez daty w API | Dz.U.: data tutaj | M.P.: bez daty w API | M.P.: data tutaj |")
print("|---|---:|---:|---:|---:|")
for dec in sorted({d for _, d in missing}):
    cells = []
    for pub in ("DU", "MP"):
        cells += [f"{missing[(pub, dec)]:,}".replace(",", " "), f"{done[(pub, dec)]:,}".replace(",", " ")]
    print(f"| {dec}–{dec + 9} | " + " | ".join(cells) + " |")
tm = sum(missing.values())
td = sum(done.values())
print(f"| razem | {sum(v for (p, _), v in missing.items() if p == 'DU'):,} | {sum(v for (p, _), v in done.items() if p == 'DU'):,} "
      f"| {sum(v for (p, _), v in missing.items() if p == 'MP'):,} | {sum(v for (p, _), v in done.items() if p == 'MP'):,} |"
      .replace(",", " "))
print(f"\n{td} / {tm} = {td / tm:.1%}", file=sys.stderr)
