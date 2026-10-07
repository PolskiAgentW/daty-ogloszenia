"""Cel 7: public files of the promulgation dates read from issue mastheads, for acts the API ELI has none for.

    python3 tools/dates_export.py OUTDIR BRAK.csv --order ORDER.csv [--fresh LISTDIR]

BRAK.csv = tools/issue_brak_list.py output (with --trust-ocr2), ORDER.csv = tools/issue_order_check.py output for it:
an issue flagged there is left out unless its date was also read from the page image, and an act dated (announcementDate)
after the issue date is always left out: either its date or its issue number in the API may be wrong.
--fresh LISTDIR (newer API year lists, tools/eli_lists_fetch.py): acts that have a promulgation there are left out,
and their API date is compared with ours (an independent check). Writes OUTDIR/numery.csv (one row per issue) and
OUTDIR/akty.csv (one row per act), column names in Polish."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("outdir")
ap.add_argument("brak")
ap.add_argument("--order", required=True)
ap.add_argument("--fresh")
a = ap.parse_args()
fresh = {}
if a.fresh:
    for f in sorted(Path(a.fresh).glob("*.json")):
        for i in json.load(f.open(encoding="utf-8"))["items"]:
            fresh[i["ELI"]] = i.get("promulgation") or ""
filled = Counter()
out = Path(a.outdir)
out.mkdir(parents=True, exist_ok=True)
unordered, act_later = set(), set()
for r in csv.DictReader(open(a.order, encoding="utf-8")):
    unordered.add((r["pub"], r["year"], r["volume"]))
    act_later.update(r["act_later"].split()[::2])  # "ELI date ELI date"


def readings(r: dict) -> str:
    parser = "warstwa tekstowa PDF" if r["parser_method"].startswith("text") else "tesseract 200 dpi"
    basis = r["basis"]
    if basis.startswith("parser+ocr300"):
        s = f"{parser} + tesseract 300 dpi"
    elif basis.startswith("obraz+parser"):
        s = f"obraz strony + {parser}"
    elif basis.startswith("obraz+ocr300"):
        s = "obraz strony + tesseract 300 dpi"
    elif basis.startswith("obraz×2"):
        s = "obraz strony ×2" + ("; odczyty maszynowe inne" if "maszynowe inne" in basis else "")
    else:
        raise SystemExit(f"unknown basis {basis!r}")
    return s + ("; trzeci odczyt inny" if "trzeci odczyt inny" in basis else "")


issues, acts, skipped, dropped = [], [], 0, 0
for r in csv.DictReader(open(a.brak, encoding="utf-8")):
    key = (r["pub"], r["year"], r["volume"])
    if key in unordered and not r["basis"].startswith("obraz"):
        skipped += 1
        continue
    how = readings(r)
    elis = [e for e in r["eli_brak"].split() if e not in act_later]
    dropped += len(r["eli_brak"].split()) - len(elis)
    if a.fresh:
        for e in [e for e in elis if fresh.get(e)]:
            same = fresh[e] == r["issue_date"]
            filled["same" if same else "other"] += 1
            if not same:
                print("filled in the API with another date:", e, fresh[e], "ours", r["issue_date"], r["basis"])
        elis = [e for e in elis if not fresh.get(e)]
    if not elis:
        continue
    issues.append({"dziennik": r["pub"], "rok": r["year"], "numer": r["volume"], "data_ogloszenia": r["issue_date"],
                   "odczyty": how, "akt_z_winieta": r["first_eli"], "aktow_w_numerze": r["n_acts"],
                   "aktow_bez_daty_w_api": len(elis), "akty_bez_daty_w_api": " ".join(elis)})
    for eli in elis:
        acts.append({"eli": eli, "dziennik": r["pub"], "rok": r["year"], "numer": r["volume"],
                     "pozycja": eli.split("/")[2], "data_ogloszenia": r["issue_date"], "odczyty": how})
for name, rows in (("numery.csv", issues), ("akty.csv", acts)):
    with (out / name).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
print(len(issues), "issues,", len(acts), "acts;", skipped, "flagged issues without an image reading left out;", dropped,
      "acts dated after their issue left out;", dict(filled) or "", "now with a date in the API (left out)" if filled else "")
