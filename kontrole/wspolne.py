"""Wspólne: katalog z danymi API ELI, daty po polsku, tekst PDF (pdftotext).

Układ katalogu (zmienna ELI_CACHE, domyślnie ~/cache/eli; taki sam jak w eli2md):
  <PUB>/<rok>.json                lista rocznika z API (api.sejm.gov.pl/eli/acts/<PUB>/<rok>)
  <PUB>/<rok>/<poz>/meta.json     rekord aktu z API
  <PUB>/<rok>/<poz>/text.pdf      PDF aktu z API
"""
import json
import os
import re
import subprocess
from pathlib import Path

API = "https://api.sejm.gov.pl/eli/acts"
UA = "eli-kontrole/1.0 (+https://github.com/PolskiAgentW/daty-ogloszenia; 1 zapytanie naraz)"
CACHE = Path(os.environ.get("ELI_CACHE", Path.home() / "cache" / "eli"))

MONTHS = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września",
          "października", "listopada", "grudnia"]
# polskie litery jako dowolny znak: warstwa tekstowa starszych PDF-ów ma czasem inne kodowanie („paêdziernika”)
MONTH_PATS = [re.sub(r"[^a-z]", ".", m) for m in MONTHS]


def month_no(word: str) -> int:
    return next(i for i, pat in enumerate(MONTH_PATS, 1) if re.fullmatch(pat, word.lower()))


def iso(day: str, month: str, year: str) -> str:
    return f"{int(year):04d}-{month_no(month):02d}-{int(day):02d}"


def years(spec: str) -> range:
    """„2000-2011” albo „2026”."""
    a, _, b = spec.partition("-")
    return range(int(a), int(b or a) + 1)


def list_items(pub: str, year: int) -> list[dict]:
    f = CACHE / pub / f"{year}.json"
    return json.loads(f.read_text(encoding="utf-8"))["items"] if f.exists() else []


def act_dir(eli: str) -> Path:
    return CACHE / eli


def cached_acts(pub: str, yrs: range):
    """(meta, ścieżka text.pdf) dla każdego aktu z PDF-em i meta.json w katalogu, w kolejności pozycji."""
    for y in yrs:
        base = CACHE / pub / str(y)
        if not base.is_dir():
            continue
        for p in sorted(base.iterdir(), key=lambda d: (len(d.name), d.name)):
            pdf, mf = p / "text.pdf", p / "meta.json"
            if pdf.exists() and mf.exists():
                try:
                    yield json.loads(mf.read_text(encoding="utf-8")), pdf
                except ValueError:
                    continue


def pdftext(pdf: Path, first: int | None = None, last: int | None = None, layout: bool = False) -> str:
    cmd = ["pdftotext"]
    if first:
        cmd += ["-f", str(first)]
    if last:
        cmd += ["-l", str(last)]
    if layout:
        cmd.append("-layout")
    try:
        return subprocess.run(cmd + [str(pdf), "-"], capture_output=True, text=True, errors="replace",
                              timeout=120).stdout
    except (OSError, subprocess.SubprocessError):
        return ""
