"""Pobiera z API ELI listy roczników oraz rekordy i PDF-y aktów do katalogu ELI_CACHE (opis w wspolne.py).

    python3 pobierz.py listy DU 1918-2026          # same listy roczników (kontrola daty_tytul.py)
    python3 pobierz.py pdf MP 2026                 # rekord + PDF każdego aktu z PDF-em (pozostałe kontrole)
    python3 pobierz.py pdf DU 2000-2011 --bez-html # tylko akty, które API daje wyłącznie jako PDF

Jedno zapytanie naraz, przerwa --pauza sekund (domyślnie 1). Pliki już pobrane są pomijane, więc można przerwać
i wznowić. Cały Dz.U. i M.P. to ok. 165 tys. aktów: przy 1 s przerwy kilka dni pobierania."""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request

from wspolne import API, CACHE, UA, list_items, years


def get(url: str) -> bytes | None:
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            err = e
        except OSError as e:
            err = e
        time.sleep(10 * 2 ** attempt)
    raise SystemExit(f"{url}: {err}")


def save(path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    tmp.write_bytes(data)
    tmp.rename(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("co", choices=("listy", "pdf"))
    ap.add_argument("pub", choices=("DU", "MP"))
    ap.add_argument("lata")
    ap.add_argument("--bez-html", action="store_true", help="tylko akty bez tekstu HTML w API")
    ap.add_argument("--pauza", type=float, default=1.0)
    a = ap.parse_args()
    for y in years(a.lata):
        f = CACHE / a.pub / f"{y}.json"
        if not f.exists():
            data = get(f"{API}/{a.pub}/{y}")
            time.sleep(a.pauza)
            if data is None:
                continue
            save(f, data)
        if a.co == "listy":
            print(a.pub, y, "lista", flush=True)
            continue
        n = 0
        for it in list_items(a.pub, y):
            if not it.get("textPDF") or (a.bez_html and it.get("textHTML")):
                continue
            d = CACHE / a.pub / str(y) / str(it["pos"])
            if not (d / "meta.json").exists():
                data = get(f"{API}/{a.pub}/{y}/{it['pos']}")
                time.sleep(a.pauza)
                if data is None or not json.loads(data).get("textPDF"):
                    continue
                save(d / "meta.json", data)
            pdf = d / "text.pdf"
            if not pdf.exists() or pdf.stat().st_size == 0:
                data = get(f"{API}/{a.pub}/{y}/{it['pos']}/text.pdf")
                time.sleep(a.pauza)
                if data is None:
                    continue
                save(pdf, data)
            n += 1
        print(a.pub, y, "aktów z PDF:", n, flush=True, file=sys.stderr)


if __name__ == "__main__":
    main()
