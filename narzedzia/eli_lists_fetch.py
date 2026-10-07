"""Download the API ELI year lists (all acts with metadata) of DU and MP for the given years into OUTDIR/PUB-YEAR.json.

    python3 tools/eli_lists_fetch.py OUTDIR [FIRST-LAST]   (default 1918-2011; one request at a time, 1.5 s apart)"""
import sys
import time
import urllib.request
from pathlib import Path

API = "https://api.sejm.gov.pl/eli/acts"
UA = "eli-dates-check/0.1 (research; 1 request at a time)"
out = Path(sys.argv[1])
first, _, last = (sys.argv[2] if len(sys.argv) > 2 else "1918-2011").partition("-")
out.mkdir(parents=True, exist_ok=True)
for pub in ("DU", "MP"):
    for year in range(int(first), int(last) + 1):
        f = out / f"{pub}-{year}.json"
        if f.exists() and f.stat().st_size:
            continue
        for attempt in range(3):
            try:
                req = urllib.request.Request(f"{API}/{pub}/{year}", headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = r.read()
                break
            except Exception as e:  # noqa: BLE001
                if getattr(e, "code", None) == 404:
                    data = None
                    break
                print(pub, year, "retry", e, flush=True)
                time.sleep(10)
        else:
            raise SystemExit(f"{pub} {year}: failed")
        if data:
            tmp = f.with_suffix(".part")
            tmp.write_bytes(data)
            tmp.rename(f)
        print(pub, year, len(data or b""), flush=True)
        time.sleep(1.5)
print("done", flush=True)
