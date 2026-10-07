"""Cel 7, stage 2: acts with no promulgation in the API, grouped by issue, with the masthead date of the issue.

One row per issue (the form offered to ISAP in the batch-3 mail, sent only after their answer): pub, year, volume,
masthead date, the readings behind it, the ELI of the first act (whose PDF page 1 shows the masthead), the number of
acts in the issue, how many of them already have this promulgation in the API (n_same), and the ELI of the acts
without promulgation.

Readings of an issue's masthead date:
  p   the parser, tools/issue_dates.py (text layer of the PDF = the publisher's OCR, else tesseract 200 dpi),
  t   tools/issue_dates2.py (tesseract 300 dpi; ~/ext/issues/issue_dates2_*.csv); ignored if its year is not the
      journal year (or the next year in January), as issue_prom_cands.plausible does for p,
  img the page image (~/ext/issues/wverify/*.jsonl, INSTRUKCJA_W.md), only if readable, masthead number = volume,
      not a reprint and of a plausible year (as t). An issue may be read from the image twice (two lists, two readers): differing image readings send
      it to OUT_rest.csv; two equal ones count as two readings ("obraz×2"), even against agreeing machine readings.
A date is taken when two readings give it and no third reading contradicts it, except that an image reading agreeing
with one of the others outvotes the third (that one misread). p and t both from tesseract (p method ocr*) count as two
readings only with --trust-ocr2 (they share the engine; measure first on images). Everything else goes to OUT_rest.csv
with the reason.

Usage: python3 tools/issue_brak_list.py OUT.csv CANDS.csv ISSUES.csv [ISSUES.csv ...] [--trust-ocr2]
(CANDS = tools/issue_prom_cands.py output, ISSUES = tools/issue_dates.py outputs for the unread issues)"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

D = Path.home() / "ext/issues"
LISTS = Path.home() / "ext/eli_lists_20261004"


def plausible(date: str, year: str) -> bool:
    """The journal year, or January of the next one."""
    return date[:4] == year or (int(date[:4]) == int(year) + 1 and date[5:7] == "01")


def decide(p: str, pm: str, t: str, imgs: list[str], trust_ocr2: bool) -> tuple[str, str]:
    """(date, basis) or ("", reason). imgs = the readable image readings of the issue."""
    if len(set(imgs)) > 1:
        return "", "odczyty z obrazu różne"
    if imgs:
        img, others = imgs[0], [x for x in (p, t) if x]
        if img in others:
            return img, "obraz+" + ("parser" if p == img else "ocr300") + ("" if all(x == img for x in others)
                                                                            else " (trzeci odczyt inny)")
        if len(imgs) > 1:  # two readers (two models) agree: OCR misreads and picks a wrong line (MP 1947 Nr 50)
            return img, "obraz×2" + (" (odczyty maszynowe inne)" if others else "")
        return "", "obraz bez drugiego zgodnego odczytu" if not others else "obraz ≠ parser/ocr300"
    if p and t and p == t:
        if pm.startswith("ocr") and not trust_ocr2:
            return "", "parser i ocr300 zgodne, oba tesseract (bez obrazu)"
        return p, "parser+ocr300"
    if p and t:
        return "", "parser ≠ ocr300 (do obrazu)"
    return "", "jeden odczyt (do obrazu)" if (p or t) else "bez odczytu (do obrazu)"


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    trust_ocr2 = "--trust-ocr2" in sys.argv
    out, cands, sources = Path(args[0]), args[1], args[2:]
    image = {}
    for p in sorted((D / "wverify").glob("*.jsonl")):
        for line in p.open(encoding="utf-8"):
            if line.strip():
                v = json.loads(line)
                image.setdefault((v["pub"], str(v["year"]), str(v["nr"])), []).append(v)
    second = {}
    for p in sorted(D.glob("issue_dates2_*.csv")):
        for r in csv.DictReader(p.open(encoding="utf-8")):
            second[(r["pub"], r["year"], r["volume"])] = r
    acts = defaultdict(list)
    for f in sorted(LISTS.glob("*.json")):
        for i in json.load(f.open(encoding="utf-8"))["items"]:
            acts[(i["publisher"], str(i["year"]), str(i.get("volume")))].append(i)
    first = {}  # issue -> (parser date, method, quote, first_eli)
    for r in csv.DictReader(open(cands, encoding="utf-8")):
        if r["kind"] == "brak":
            first.setdefault((r["pub"], r["year"], r["volume"]), (r["issue_date"], r["method"], r["quote"],
                                                                   r["first_eli"]))
    for src in sources:
        for r in csv.DictReader(open(src, encoding="utf-8")):
            k = (r["pub"], r["year"], r["volume"])
            if not r["date"] and k not in first and re.search(r"brak×\d+", r["api_values"]):
                first[k] = ("", r["method"], "", r["first_eli"])
    rows, rest, by = [], [], Counter()
    for k in sorted(first, key=lambda k: (k[0], int(k[1]), int(k[2]) if k[2].isdigit() else 0)):
        p, pm, quote, first_eli = first[k]
        t = (second.get(k) or {}).get("date2", "")
        if t and not plausible(t, k[1]):
            t = ""  # OCR misread the year ("Rok 1522"): not a reading
        imgs, img_note = [], ""
        for v in image.get(k, []):
            if not v["readable"] or not v["date"]:
                img_note = "nieczytelny" if v.get("masthead", True) else "brak winiety na s. 1"
            elif str(v["nr_seen"]) != k[2] or v.get("reprint"):
                img_note = "numer/przedruk inny"
            elif not plausible(v["date"], k[1]):
                img_note = "rok inny"  # MP 1947 Nr 41: the PDF is M.P. 1946 Nr 41 (13 May 1946), read right twice
            else:
                imgs.append(v["date"])
        date, basis = decide(p, pm, t, imgs, trust_ocr2)
        items = acts[k]
        brak = sorted((i for i in items if not i.get("promulgation")), key=lambda i: i["pos"])
        row = {"pub": k[0], "year": k[1], "volume": k[2], "issue_date": date, "basis": basis, "parser": p,
               "parser_method": pm, "ocr300": t, "image": " ".join(imgs) or img_note, "first_eli": first_eli,
               "n_acts": len(items), "n_same": sum(i.get("promulgation") == date for i in items) if date else "",
               "n_brak": len(brak), "eli_brak": " ".join(i["ELI"] for i in brak), "quote": quote}
        (rows if date else rest).append(row)
        by[(k[0], int(k[1]) // 10 * 10, basis if date else "rest: " + basis)] += len(brak)
    for path, part in ((out, rows), (out.with_name(out.stem + "_rest.csv"), rest)):
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, list((rows or rest)[0]))
            w.writeheader()
            w.writerows(part)
    print(len(rows), "issues /", sum(r["n_brak"] for r in rows), "acts with a date;", len(rest), "issues /",
          sum(r["n_brak"] for r in rest), "acts left out")
    tot = Counter()
    for (pub, dec, basis), n in by.items():
        tot[basis] += n
    for b, n in tot.most_common():
        print(f"  {n:6d}  {b}")


if __name__ == "__main__":
    main()
