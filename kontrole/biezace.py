"""Codzienna kontrola bieżących rekordów API ELI (w GitHub Actions: .github/workflows/biezace.yml).

Bierze akty Dz.U. i M.P., których promulgation albo announcementDate przypada w ostatnich --dni dniach, i przepuszcza
je przez kontrole 1–5 (daty_tytul.py, zly_pdf.py, numer_tytulu.py, metadane.py, naglowek_2012.py). Przy wierszach
o promulgation dopisuje „Data ogłoszenia” ze strony wydawcy (dziennikustaw.gov.pl, monitorpolski.gov.pl), czyli drugie
źródło obok druku.

    python3 biezace.py KATALOG [--dni 90] [--pauza 1] [--budzet 40] [--przytnij]

W KATALOGU zapisuje:
  kandydaci.csv  wiersz = kandydat (opis kolumn w README.md katalogu); kolumna od = pierwszy dzień, w którym
                 kontrola go wskazała (z poprzedniej wersji pliku), więc widać, jak długo różnica jest w API,
  stan.json      data przebiegu, okno, liczba aktów i kandydatów.
Listy roczników pobiera za każdym razem od nowa: meta.json = pozycja z listy, czyli stan API na dziś. PDF-y trzyma
w ELI_CACHE i pobiera ponownie tylko wtedy, gdy w liście zmienił się changeDate aktu. --przytnij usuwa z ELI_CACHE
PDF-y aktów spoza okna (tylko dla katalogu używanego wyłącznie przez tę kontrolę). Po --budzet minutach pobierania
akty bez PDF-u zostają na następny przebieg (stan.json: aktow_z_pdf < aktow). Jedno zapytanie naraz."""
import argparse
import csv
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from pobierz import get, save
from wspolne import API, CACHE

HERE = Path(__file__).resolve().parent
WYDAWCA = {"DU": "https://dziennikustaw.gov.pl", "MP": "https://monitorpolski.gov.pl"}
DATA_OGL = re.compile(r"Data ogłoszenia:\s*(?:<[^>]+>\s*)*(\d{4}-\d{2}-\d{2})")
POLA = ["eli", "kontrola", "pole", "w_API", "inna_wartosc", "zrodlo_innej_wartosci", "wydawca", "od", "tytul"]


def okno(od: str, lata: range, tmp: Path, pauza: float) -> list[dict]:
    acts = []
    for pub in ("DU", "MP"):
        for y in lata:
            data = get(f"{API}/{pub}/{y}")
            time.sleep(pauza)
            if data is None:
                continue
            save(tmp / pub / f"{y}.json", data)
            acts += [it for it in json.loads(data)["items"]
                     if max(it.get("promulgation") or "", it.get("announcementDate") or "") >= od]
    return acts


def pdfy(acts: list[dict], tmp: Path, pauza: float, budzet: float) -> tuple[int, int]:
    """Katalog roboczy w układzie ELI_CACHE: meta.json z listy, text.pdf jako dowiązanie do PDF-u w ELI_CACHE.
    Po budzet minutach nie pobiera już PDF-ów (te akty sprawdzi następny przebieg); stary PDF zostaje w użyciu."""
    have = got = 0
    end = time.monotonic() + budzet * 60
    for it in acts:
        if not it.get("textPDF"):
            continue
        d = CACHE / it["ELI"]
        pdf, stamp = d / "text.pdf", d / "changeDate"
        change = it.get("changeDate") or ""
        stale = not pdf.exists() or not stamp.exists() or stamp.read_text() != change
        if stale and time.monotonic() > end:
            if not pdf.exists():
                continue
        elif stale:
            data = get(f"{API}/{it['ELI']}/text.pdf")
            time.sleep(pauza)
            if data is None:
                continue
            save(pdf, data)
            stamp.write_text(change)
            got += 1
            if got % 100 == 0:
                print(f"pobrane PDF-y: {got}, {budzet - (end - time.monotonic()) / 60:.0f} min", file=sys.stderr,
                      flush=True)
        w = tmp / it["ELI"]
        w.mkdir(parents=True, exist_ok=True)
        (w / "meta.json").write_text(json.dumps(it, ensure_ascii=False), encoding="utf-8")
        (w / "text.pdf").symlink_to(pdf.resolve())
        have += 1
    return have, got


def przytnij(acts: list[dict]) -> int:
    keep = {it["ELI"] for it in acts}
    n = 0
    for pub in ("DU", "MP"):
        for d in CACHE.glob(f"{pub}/*/*"):
            if d.is_dir() and f"{pub}/{d.parent.name}/{d.name}" not in keep:
                shutil.rmtree(d)
                n += 1
    return n


def kontrole(tmp: Path, lata: str, out: Path) -> None:
    env = dict(os.environ, ELI_CACHE=str(tmp))

    def run(*args):
        subprocess.run([sys.executable, *args], cwd=HERE, env=env, check=True)

    run("daty_tytul.py", str(out / "k1.csv"), "--lata", lata)
    for pub in ("DU", "MP"):
        run("zly_pdf.py", "--pub", pub, "--lata", lata, str(out / f"k2_{pub}.csv"))
        run("numer_tytulu.py", "--pub", pub, "--lata", lata, str(out / f"k3_{pub}.csv"))
        run("metadane.py", "--pub", pub, "--lata", lata, str(out / f"k4_{pub}.csv"))
    run("naglowek_2012.py", "--lata", lata, str(out / "k5.csv"))


def wiersze(out: Path):
    """Wyniki kontroli 1–5 jako wiersze w jednym formacie (tylko kandydaci)."""
    def read(name):
        f = out / name
        return list(csv.DictReader(open(f, encoding="utf-8"))) if f.exists() else []

    for r in read("k1.csv"):
        if r["pole"] == "announcementDate":
            yield r["eli"], "daty_tytul", "announcementDate", r["wartosc_w_API"], r["oczekiwana"], r["uwaga"]
        elif r["pole"] == "announcementDate>promulgation":
            yield r["eli"], "daty_tytul", "announcementDate>promulgation", r["wartosc_w_API"], r["oczekiwana"], \
                "promulgation w API"
        else:
            yield r["eli"], "daty_tytul", r["pole"], r["wartosc_w_API"], "", r["uwaga"]
    for pub in ("DU", "MP"):
        for r in read(f"k2_{pub}.csv"):
            if r["wynik"] == "KANDYDAT":
                yield r["eli"], "zly_pdf", "PDF", f"poz. {r['pozycja']}", f"poz. {r['poz_w_pdf']}", \
                    "numery pozycji w PDF-ie"
        for r in read(f"k3_{pub}.csv"):
            if r["wynik"] == "BRAK":
                yield r["eli"], "numer_tytulu", "numer w tytule", r["nr"], "", "brak tego numeru w PDF-ie"
        for r in read(f"k4_{pub}.csv"):
            if "DATA" in r["wynik"]:
                yield r["eli"], "metadane", "data w tytule", r["data_w_tytule"], r["data_w_naglowku"], \
                    "nagłówek aktu w PDF-ie"
            if "NR" in r["wynik"]:
                yield r["eli"], "metadane", "numer w tytule", r["nr_w_tytule"], r["nr_w_naglowku"], \
                    "nagłówek aktu w PDF-ie"
    for r in read("k5.csv"):
        if r["wynik"] in ("INNA", "BRAK_W_API"):
            yield r["eli"], "naglowek_2012", "promulgation", r["promulgation"], r["data_w_naglowku"], \
                f"nagłówek PDF: {r['cytat']}"


def wydawca(eli: str, pauza: float, nie_dziala: set) -> str:
    pub = eli.split("/")[0]
    if pub in nie_dziala:
        return "błąd pobrania"
    try:
        data = get(f"{WYDAWCA[pub]}/{eli}")
    except SystemExit:  # get() po 4 nieudanych próbach: tej strony już nie pytamy, kontrola idzie dalej
        nie_dziala.add(pub)
        return "błąd pobrania"
    time.sleep(pauza)
    m = DATA_OGL.search(html.unescape(data.decode("utf-8", "replace"))) if data else None
    return m[1] if m else "brak"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("katalog")
    ap.add_argument("--dni", type=int, default=90)
    ap.add_argument("--pauza", type=float, default=1.0)
    ap.add_argument("--przytnij", action="store_true")
    ap.add_argument("--budzet", type=float, default=40, help="minuty na pobieranie PDF-ów")
    a = ap.parse_args()
    dest = Path(a.katalog)
    dest.mkdir(parents=True, exist_ok=True)
    today = dt.date.today()
    od = (today - dt.timedelta(days=a.dni)).isoformat()
    lata = range(int(od[:4]), today.year + 1)
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t) / "okno"
        acts = okno(od, lata, tmp, a.pauza)
        have, got = pdfy(acts, tmp, a.pauza, a.budzet)
        cut = przytnij(acts) if a.przytnij else 0
        print(f"okno od {od}: {len(acts)} aktów, z PDF-em {have}, pobrane PDF-y {got}, usunięte z cache {cut}",
              file=sys.stderr)
        out = Path(t) / "wyniki"
        out.mkdir()
        kontrole(tmp, f"{lata.start}-{lata.stop - 1}", out)
        titles = {it["ELI"]: it.get("title") or "" for it in acts}
        rows = [r for r in wiersze(out) if r[0] in titles]
    old = {}
    f = dest / "kandydaci.csv"
    if f.exists():
        old = {(r["eli"], r["kontrola"], r["pole"], r["w_API"]): r for r in csv.DictReader(open(f, encoding="utf-8"))}
    res, nie_dziala = [], set()
    for eli, kontrola, pole, val, other, src in sorted(set(rows)):
        prev = old.get((eli, kontrola, pole, val))
        pub_date = ""
        if "promulgation" in pole:
            pub_date = wydawca(eli, a.pauza, nie_dziala)
        res.append({"eli": eli, "kontrola": kontrola, "pole": pole, "w_API": val, "inna_wartosc": other,
                    "zrodlo_innej_wartosci": src, "wydawca": pub_date,
                    "od": prev["od"] if prev else today.isoformat(), "tytul": titles[eli][:200]})
    with open(f, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=POLA)
        w.writeheader()
        w.writerows(res)
    last = max(it.get("promulgation") or "" for it in acts) if acts else ""
    stan = {"data": today.isoformat(), "okno_od": od, "aktow": len(acts), "aktow_z_pdf": have,
            "kandydatow": len(res), "najnowsza_promulgation": last}
    (dest / "stan.json").write_text(json.dumps(stan, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(stan, file=sys.stderr)
    # Zielony przebieg bez kandydatów wygląda jak zdrowy. Najdłuższa przerwa w ogłaszaniu aktów w 2025–2026 to 6 dni,
    # więc brak nowego aktu przez 10 dni oznacza awarię (listy API albo tej kontroli).
    if not last or (today - dt.date.fromisoformat(last)).days > 10:
        sys.exit(f"najnowszy akt w listach ogłoszono {last or '?'}: listy API nieaktualne albo kontrola nie działa")


if __name__ == "__main__":
    main()
