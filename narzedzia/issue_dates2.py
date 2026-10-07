"""Cel 7, stage 2: a second, automatic reading of the masthead date of every issue with "brak" acts.

The first reading (tools/issue_dates.py) takes the text layer of the PDF when it has a date (the publisher's OCR) and
tesseract at 200 dpi only when it has none. The control sample on page images (wlists --sample 60, 2026-10-07) found
1 wrong date in 60: MP 1962 Nr 20, text layer "3 marca", image "8 marca". This reads the same masthead again from the
page image, always with tesseract at 300 dpi (top 30 % with all patterns, then top 50 % with masthead-only patterns),
so an issue read from the text layer gets a reading independent of it. For issues whose first reading was already
tesseract (method ocr/ocr50) the second reading differs only in resolution: report those agreements separately.
Last pass "strip": the masthead band only (top 1.5–8 % of the page), psm 6 then 11, with the M.P. 1946–1950 masthead
"Nr 92  Warszawa, 2 lipca [eagle] 1947 roku  Rok XXVI" (no "dnia", the eagle between month and year).

--none ISSUES.csv: instead of CANDS, the issues of tools/issue_dates.py output with no date read and at least one act
without promulgation (date1 = ""); a date found here is a single reading, to be checked on the image.

Writes OUT.csv (append, resumable): pub, year, volume, first_eli, date1, method1, date2, method2, quote2.
Only cached PDFs, no network.

Usage: python3 tools/issue_dates2.py OUT.csv CANDS.csv [--workers 3] [--kinds brak,inna] [--none]"""
import argparse
import csv
import re
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from issue_dates import CACHE, DAY, MONTH, find, iso, page_size  # noqa: E402

DPI = 300
STRIP = re.compile(r"[\\VW]\s?ar\S{0,3}[sś]\S{0,4}a\W{0,4}(?:dnia\s+)?" + DAY + r"\s+" + MONTH
                   + r"[\s\S]{0,40}?\b(1[89]\d\d)\s*(?:roku|r\.)", re.I)
lock = threading.Lock()


def ocr(pdf: Path, top: float, psm: str = "3", y0: float = 0) -> str:
    w, h = page_size(pdf)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", str(DPI), "-f", "1", "-l", "1", "-gray", "-png", "-x", "0", "-y",
                        str(int(h * y0 / 72 * DPI)), "-W", str(int(w / 72 * DPI) + 1),
                        "-H", str(int(h * (top - y0) / 72 * DPI)), str(pdf), f"{tmp}/p"],
                       check=True, capture_output=True)
        png = next(Path(tmp).glob("p*.png"))
        return subprocess.run(["tesseract", str(png), "-", "-l", "pol", "--psm", psm], capture_output=True, text=True,
                              env={"OMP_THREAD_LIMIT": "1", "PATH": "/usr/bin:/bin"}).stdout


def read2(pdf: Path) -> tuple[str, str, str]:
    for method, top, psm, masthead_only in (("ocr300", 0.3, "3", False), ("ocr300psm6", 0.3, "6", False),
                                            ("ocr300_50", 0.5, "3", True)):
        hit = find(ocr(pdf, top, psm), masthead_only=masthead_only)
        if hit:
            return hit[0], f"{method}:{hit[1]}", hit[2]
    for psm in ("6", "11"):
        text = " ".join(ocr(pdf, 0.08, psm, 0.015).split())
        for m in STRIP.finditer(text):
            d = iso(m[1], m[2], m[3])
            if d:
                return d, f"strip_psm{psm}:mp_rok", text[max(0, m.start() - 10):m.end()][:160]
    return "", "none", ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("cands")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--kinds", default="brak")
    ap.add_argument("--none", action="store_true", help="CANDS is an issue_dates.py output: take unread issues")
    a = ap.parse_args()
    kinds = set(a.kinds.split(","))
    issues = {}
    for r in csv.DictReader(open(a.cands, encoding="utf-8")):
        if a.none and not r["date"] and "brak" in r["api_values"]:
            issues[(r["pub"], r["year"], r["volume"])] = {**r, "issue_date": ""}
        elif not a.none and r["kind"] in kinds:
            issues.setdefault((r["pub"], r["year"], r["volume"]), r)
    out = Path(a.out)
    done = set()
    if out.exists():
        done = {(r["pub"], r["year"], r["volume"]) for r in csv.DictReader(out.open(encoding="utf-8"))}
    todo = [k for k in sorted(issues, key=lambda k: (k[0], int(k[1]), int(k[2]) if k[2].isdigit() else 0))
            if k not in done]
    print(len(issues), "issues,", len(todo), "to do", flush=True)
    fields = ["pub", "year", "volume", "first_eli", "date1", "method1", "date2", "method2", "quote2"]
    new = not out.exists()
    with out.open("a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fields)
        if new:
            w.writeheader()

        def work(k):
            r = issues[k]
            pub, year, pos = r["first_eli"].split("/")
            try:
                d2, m2, q2 = read2(CACHE / pub / year / pos / "text.pdf")
            except Exception as e:  # noqa: BLE001 - one issue must not stop the run
                print("error", k, e, flush=True)
                return
            with lock:
                w.writerow({"pub": k[0], "year": k[1], "volume": k[2], "first_eli": r["first_eli"],
                            "date1": r["issue_date"], "method1": r["method"], "date2": d2, "method2": m2, "quote2": q2})
                fh.flush()

        with ThreadPoolExecutor(a.workers) as ex:
            for n, _ in enumerate(ex.map(work, todo), 1):
                if n % 200 == 0:
                    print(f"{n}/{len(todo)}", time.strftime("%H:%M:%S"), flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
