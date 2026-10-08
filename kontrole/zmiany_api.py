"""Czy zgłoszone wartości zmieniły się w API ELI (stan teraz, rekord po rekordzie).

Wejście: CSV z kolumnami eli, pole, wartosc_w_API, wartosc_wg_PDF_lub_tytulu (format list wysyłanych do ISAP).
  pole = announcementDate / promulgation / inne pole rekordu: porównanie pola z wartością zgłoszoną jako niezgodna,
  pole = title: wartosc_w_API to niezgodny fragment „z dnia …” tytułu; zmiana = tytuł go już nie ma,
               poprawione = tytuł ma teraz datę z druku („z dnia D miesiąca RRRR”).
Wypisuje każdy zmieniony wiersz i podsumowanie: poprawione wg druku, zmienione inaczej, bez zmian, błędy.

    python3 zmiany_api.py ZGLOSZONE.csv [--pauza 0.2]"""
import argparse
import csv
import json
import time
import urllib.request

from wspolne import API, MONTHS, UA


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--pauza", type=float, default=0.2)
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.csv, encoding="utf-8")))
    acts: dict[str, dict | None] = {}
    fixed = other = same = errors = 0
    for r in rows:
        eli = r["eli"]
        if eli not in acts:
            acts[eli] = None
            for attempt in range(3):
                try:
                    req = urllib.request.Request(f"{API}/{eli}", headers={"User-Agent": UA})
                    acts[eli] = json.load(urllib.request.urlopen(req, timeout=30))
                    break
                except (OSError, ValueError):
                    time.sleep(5 * (attempt + 1))
            time.sleep(a.pauza)
        act = acts[eli]
        if act is None:
            errors += 1
            continue
        wrong, good = r["wartosc_w_API"], r["wartosc_wg_PDF_lub_tytulu"]
        if r["pole"] == "title":
            value = act.get("title") or ""
            if wrong in value:
                same += 1
                continue
            y, m, d = good.split("-")
            ok = f"z dnia {int(d)} {MONTHS[int(m) - 1]} {y}" in value
        else:
            value = act.get(r["pole"])
            if value == wrong:
                same += 1
                continue
            ok = value == good
        fixed += ok
        other += not ok
        print("POPRAWIONE" if ok else "ZMIANA", eli, r["pole"], wrong, "->", value, "(wg druku:", good + ")")
    print("wiersze", len(rows), "poprawione_wg_druku", fixed, "zmienione_inaczej", other, "bez_zmian", same,
          "bledy", errors)


if __name__ == "__main__":
    main()
