"""Append one masthead reading to OUT (INSTRUKCJA_W.md).
python3 /home/ai/ext/issues/wadd.py OUT --pub DU --year 1938 --nr 36 --masthead yes --date 1938-05-20 --nr-seen 36 \
    --readable yes --reprint no --note "Winieta: ..."   (--date none / --nr-seen none when not readable)"""
import argparse
import json
import re

yn = {"yes": True, "no": False}
ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--pub", required=True, choices=("DU", "MP"))
ap.add_argument("--year", type=int, required=True)
ap.add_argument("--nr", type=int, required=True)
ap.add_argument("--masthead", required=True, choices=yn)
ap.add_argument("--date", required=True)
ap.add_argument("--nr-seen", required=True)
ap.add_argument("--readable", required=True, choices=yn)
ap.add_argument("--reprint", required=True, choices=yn)
ap.add_argument("--note", required=True)
a = ap.parse_args()
if a.date != "none" and not re.fullmatch(r"\d{4}-\d\d-\d\d", a.date):
    raise SystemExit("--date must be YYYY-MM-DD or none")
row = {"pub": a.pub, "year": a.year, "nr": a.nr, "masthead": yn[a.masthead],
       "date": None if a.date == "none" else a.date,
       "nr_seen": None if a.nr_seen == "none" else int(a.nr_seen), "readable": yn[a.readable],
       "reprint": yn[a.reprint], "note": a.note}
with open(a.out, "a", encoding="utf-8") as f:
    f.write(json.dumps(row, ensure_ascii=False) + "\n")
print("ok", a.pub, a.year, a.nr, row["date"])
