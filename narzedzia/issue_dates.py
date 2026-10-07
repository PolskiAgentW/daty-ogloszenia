"""Cel 7, stage 2: the date printed on the first page of every journal issue (Dz.U. and M.P. before 2012).

Every act of an issue shares its promulgation date, printed once in the issue masthead: "Warszawa, dnia 8 października
1999 r." (DU after the war, MP), "Warszawa, Piątek ... 11 lutego 1938 roku" (MP before the war), "21 grudnia ... Rok 1927"
(DU before the war). For each issue (year + volume in the API lists of 2026-10-04) take text.pdf of its first act (lowest
pos), read the top 30 % of page 1: the text layer first, else tesseract; then the top half with masthead-only
patterns. Dates in the table of contents
("z dnia ...") are skipped.

Writes OUT.csv (append, resumable): pub, year, volume, first_eli, n_acts, date, method, quote, api_majority, api_values.
PDFs go to the shared cache ~/cache/eli/<PUB>/<YEAR>/<POS>/text.pdf.

Usage: python3 tools/issue_dates.py OUT.csv [--workers 2] [--only DU|MP] [--from-year Y] [--before Y] [--cached-only]"""
import argparse
import csv
import json
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WS / "tools"))
from isap_resolve import MONTH_PATS  # noqa: E402

LISTS = Path.home() / "ext/eli_lists_20261004"
CACHE = Path.home() / "cache/eli"
API = "https://api.sejm.gov.pl/eli/acts"
MONTH = "(" + "|".join(MONTH_PATS) + ")"
DAY = r"([\dlI]{1,2})"  # OCR reads 1 as l or I ("dnia l czerwca 1978")
WEEKDAYS = r"(?:poniedzia\S*|wtorek|\S{0,2}roda|czwartek|pi\S{0,2}tek|sobota|niedziela)"
PATTERNS = [  # (method, regex with groups day, month, year)
    ("warszawa_nr", re.compile(r"[\\VW]\s?AR\S{0,3}[SŚ]\S{0,4}A\W{0,4}(?:N\S{0,2}|№|J\S|Nr)\.?\s*\d+\W{0,4}" + DAY + r"\s+"
                               + MONTH + r"\s+(\d{4})", re.I)),
    ("warszawa", re.compile(r"[\\VW]\s?ar\S{0,3}[sś]\S{0,4}a\W{0,4}(?:Nr\s*\d+\W{0,3})?dnia\s+" + DAY + r"\s+" + MONTH
                            + r"\s+(\d{4})", re.I)),
    ("mp_weekday", re.compile(r"[\\VW]\s?ar\S{0,3}[sś]\S{0,4}a\W{0,4}" + WEEKDAYS + r"[\s\S]{0,80}?\b" + DAY + r"\s+"
                              + MONTH + r"\s+(\d{4})\s+roku", re.I)),
    ("dp_warszawa", re.compile(r"W\s?A\s?R\s?S\s?Z\s?A\s?W\s?A\W[\s\S]{0,60}?(?<!dnia )(?<!dn\. )\b" + DAY + r"\s+" + MONTH
                               + r"\s+(\d{4})")),  # Dziennik Praw 1918-1919; only in the masthead-only pass
    ("du_rok", re.compile(r"(?<!dnia )(?<!dn\. )\b" + DAY + r"\s+" + MONTH + r"[\s\S]{0,80}?Rok\s+(\d{4})", re.I)),
]
lock = threading.Lock()


def iso(day: str, month: str, year: str) -> str | None:
    day = re.sub("[lIiL]", "1", day)  # DAY is matched with re.I, so "i"/"L" too
    m = next((i for i, pat in enumerate(MONTH_PATS, 1) if re.fullmatch(pat, month.lower())), None)
    if m is None or not 1 <= int(day) <= 31:
        return None
    return f"{int(year):04d}-{m:02d}-{int(day):02d}"


def find(text: str, masthead_only: bool = False) -> tuple[str, str, str] | None:
    head = "\n".join(text.splitlines()[:60])
    for method, rx in PATTERNS:
        if masthead_only and method == "warszawa":  # "Warszawa, dnia ..." also ends acts lower on the page
            continue
        if not masthead_only and method == "dp_warszawa":
            continue
        for m in rx.finditer(head):
            d = iso(m[1], m[2], m[3])
            if d:
                return d, method, re.sub(r"\s+", " ", head[max(0, m.start() - 10):m.end()])[:160]
    return None


def get(url: str) -> bytes:
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - retry any network error
            if attempt == 3:
                raise
            print("retry", url, e, flush=True)
            time.sleep(10 * (attempt + 1))
    raise AssertionError


TOP = 0.3  # the masthead is in the top 30 % of page 1


def page_size(pdf: Path) -> tuple[float, float]:
    info = subprocess.run(["pdfinfo", "-f", "1", "-l", "1", str(pdf)], capture_output=True, text=True).stdout
    m = re.search(r"Page\s+1 size:\s+([\d.]+) x ([\d.]+)", info) or re.search(r"Page size:\s+([\d.]+) x ([\d.]+)", info)
    return float(m[1]), float(m[2])


def page1_top_text(pdf: Path, top: float = TOP) -> str:
    w, h = page_size(pdf)
    return subprocess.run(["pdftotext", "-f", "1", "-l", "1", "-x", "0", "-y", "0", "-W", str(int(w) + 1), "-H",
                           str(int(h * top)), str(pdf), "-"], capture_output=True, text=True, errors="replace").stdout


def page1_ocr(pdf: Path, top: float = TOP) -> str:
    w, h = page_size(pdf)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", "200", "-f", "1", "-l", "1", "-gray", "-png", "-x", "0", "-y", "0",
                        "-W", str(int(w / 72 * 200) + 1), "-H", str(int(h * top / 72 * 200)), str(pdf), f"{tmp}/p"],
                       check=True, capture_output=True)
        png = next(Path(tmp).glob("p*.png"))
        return subprocess.run(["tesseract", str(png), "-", "-l", "pol", "--psm", "3"], capture_output=True, text=True,
                              env={"OMP_THREAD_LIMIT": "1", "PATH": "/usr/bin:/bin"}).stdout


def issue_row(key, acts) -> dict:
    pub, year, vol = key
    first = min(acts, key=lambda a: a["pos"])
    pdf = CACHE / pub / str(year) / str(first["pos"]) / "text.pdf"
    if not pdf.exists():
        pdf.parent.mkdir(parents=True, exist_ok=True)
        data = get(f"{API}/{first['ELI']}/text.pdf")
        tmp = pdf.with_suffix(".part")
        tmp.write_bytes(data)
        tmp.rename(pdf)
        time.sleep(0.3)
    text = page1_top_text(pdf)
    hit, method_prefix = find(text), "text"
    if not hit:
        hit, method_prefix = find(page1_ocr(pdf)), "ocr"
    if not hit:  # Dziennik Praw 1918-1919: "WARSZAWA. № 4. 5 marca 1918." lower on a small page
        hit, method_prefix = find(page1_top_text(pdf, 0.5), masthead_only=True), "text50"
    if not hit:
        hit, method_prefix = find(page1_ocr(pdf, 0.5), masthead_only=True), "ocr50"
    vals = Counter(a.get("promulgation") or "" for a in acts)
    known = Counter({k: v for k, v in vals.items() if k})
    return {"pub": pub, "year": year, "volume": vol, "first_eli": first["ELI"], "n_acts": len(acts),
            "date": hit[0] if hit else "", "method": f"{method_prefix}:{hit[1]}" if hit else "none",
            "quote": hit[2] if hit else "",
            "api_majority": known.most_common(1)[0][0] if known else "",
            "api_values": "; ".join(f"{k or 'brak'}×{v}" for k, v in vals.most_common())}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--only")
    ap.add_argument("--before", type=int, default=2012, help="only issues of years < BEFORE")
    ap.add_argument("--from-year", type=int, default=0, help="only issues of years >= FROM_YEAR")
    ap.add_argument("--cached-only", action="store_true", help="skip issues whose first PDF is not in the cache")
    a = ap.parse_args()
    issues = defaultdict(list)
    for f in sorted(LISTS.glob("*.json")):
        for i in json.load(f.open(encoding="utf-8"))["items"]:
            if a.from_year <= i["year"] < a.before and (not a.only or i["publisher"] == a.only):
                issues[(i["publisher"], i["year"], i.get("volume"))].append(i)
    out = Path(a.out)
    done = set()
    if out.exists():
        done = {(r["pub"], int(r["year"]), int(r["volume"]) if r["volume"] not in ("", "None") else None)
                for r in csv.DictReader(out.open(encoding="utf-8"))}
    todo = [k for k in sorted(issues, key=lambda k: (k[0], k[1], k[2] or 0)) if k not in done]
    if a.cached_only:
        todo = [k for k in todo if (CACHE / k[0] / str(k[1]) / str(min(a2["pos"] for a2 in issues[k])) / "text.pdf").exists()]
    print(len(issues), "issues,", len(todo), "to do", flush=True)
    fields = ["pub", "year", "volume", "first_eli", "n_acts", "date", "method", "quote", "api_majority", "api_values"]
    new = not out.exists()
    with out.open("a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fields)
        if new:
            w.writeheader()

        def work(k):
            try:
                row = issue_row(k, issues[k])
            except Exception as e:  # noqa: BLE001 - one issue must not stop the run
                print("error", k, e, flush=True)
                return
            with lock:
                w.writerow(row)
                fh.flush()

        with ThreadPoolExecutor(a.workers) as ex:
            for n, _ in enumerate(ex.map(work, todo), 1):
                if n % 200 == 0:
                    print(f"{n}/{len(todo)}", time.strftime("%H:%M:%S"), flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
