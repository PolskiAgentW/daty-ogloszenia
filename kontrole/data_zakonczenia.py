"""Kontrola 6: data aktu z formuły końcowej tekstu, dla aktów bez daty w tytule (Dz.U. 1918–1989).

Część aktów z pierwszych lat (głównie rozporządzenia i dekrety 1918–1920) ma w API tytuł bez daty, więc
kontrola 1 nie ma z czym porównać `announcementDate`. Data jest w druku w formule końcowej, przed podpisami:
„Warszawa, dnia 28 kwietnia 1919 r.”, „Warszawa. dn. 12 marca 1920 r.”,
„Dan w Warszawie, d. 16 grudnia 1918 r.”. Skrypt czyta tekst aktów z korpusu eli2md (OCR skanów z API)
i porównuje tę datę z `announcementDate` z index.csv.

Formuła jest szukana w ostatnich 8 niepustych wierszach tekstu (wygrywa ostatnia), z pominięciem przywołań
(„z dnia …”, „od dnia …”) i dat wejścia w życie („wchodzi w życie dnia …”). Jeśli jej tam nie ma, w całym
tekście szukana jest formuła z nazwą miejsca („Warszawa, 7 października 1918 r.”, także przed załącznikami).

Umowy międzynarodowe są pomijane, jak w kontroli 1 (API podaje przy nich datę podpisania albo ratyfikacji).

Wynik to kandydaci. Tekst aktu w korpusie bywa wycięty z sąsiednią pozycją, więc ostatnia data może należeć
do następnego albo poprzedniego aktu; formuła może też być przywołaniem albo datą wejścia w życie. Rozstrzyga
obraz strony PDF-u (README.md, „Zmierzona trafność”).

    python3 data_zakonczenia.py KORPUS WYNIK.csv [--lata 1918-1989]

KORPUS: katalog korpusu eli2md (index.csv i DU/<rok>/DU-<rok>-<poz>.md), np. dziennik-ustaw-1918-1989-md.
Wynik: eli, announcementDate, data_z_tekstu, werdykt (zgodna / brak daty w tekście / inna), cytat, tytuł."""
import argparse
import csv
import re
from pathlib import Path

from wspolne import MONTH_PATS, month_no, years

MON = "(" + "|".join(MONTH_PATS) + ")"
DATE = r"([0-3]?[0-9lI])\s*(?:-?go)?\s+" + MON + r"\s+((?:1[89]|20)[0-9]{2})"
ANY_DATE = re.compile(r"[0-3]?[0-9]\s*(?:-?go)?\s+" + MON + r"\s+(?:1[89]|20)[0-9]{2}", re.I)
CLOSE = re.compile(r"\b(?:dnia|dniu|dn\.|d\.)\s*" + DATE, re.I)
CITE = re.compile(r"\b(?:z|od|do|ze|we|w|po|przed|życie|mocy)\s*$", re.I)
PLACE = re.compile(r"\b(?:Warszawa|W\s+Warszawie|Dan\s+w\s+\w+|Dano\s+w\s+\w+|Spała|Kraków|Poznań|Lublin|Belweder)"
                   r"[,.]?\s*(?:\S{1,5}\s+)?" + DATE, re.I)  # „dnia”, „dn.”, „d.” i ich odczyty OCR („dé”)
TREATY = re.compile(r"(Umowa|Konwencja|Protokół|Porozumienie|Układ|Traktat|Deklaracja)\b")
TAIL = 8


def iso(m: re.Match) -> str | None:
    day = int(re.sub(r"[lI]", "1", m.group(1)))
    return f"{int(m.group(3)):04d}-{month_no(m.group(2)):02d}-{day:02d}" if 1 <= day <= 31 else None


def body(md: str) -> list[str]:
    """Niepuste wiersze tekstu bez frontmattera, tytułu (H1) i uwag konwertera („> [Strona …”)."""
    if md.startswith("---"):
        end = md.find("\n---", 3)
        md = md[end + 4:] if end > 0 else md
    return [l for l in md.splitlines() if l.strip() and not l.startswith("> [") and not l.startswith("# ")]


def closing_date(lines: list[str]) -> tuple[str, str] | None:
    found = None
    for line in lines[-TAIL:]:
        for m in CLOSE.finditer(line):
            if CITE.search(line[max(0, m.start() - 8):m.start()]):
                continue
            if v := iso(m):
                found = (v, line[max(0, m.start() - 40):m.end() + 5].strip())
    if found:
        return found
    for line in lines:
        for m in PLACE.finditer(line):
            if v := iso(m):
                found = (v, line[max(0, m.start() - 40):m.end() + 5].strip())
    return found


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("korpus")
    ap.add_argument("wynik")
    ap.add_argument("--lata", default="1918-1989")
    a = ap.parse_args()
    root, yrs = Path(a.korpus), set(years(a.lata))
    counts: dict[str, int] = {}
    with open(root / "index.csv", newline="", encoding="utf-8") as f, \
            open(a.wynik, "w", newline="", encoding="utf-8") as out:
        w = csv.writer(out)
        w.writerow(["eli", "announcementDate", "data_z_tekstu", "werdykt", "cytat", "tytul"])
        for r in csv.DictReader(f):
            if r["status"] != "ok" or int(r["year"]) not in yrs or ANY_DATE.search(r["title"]) \
                    or TREATY.match(r["type"]):
                continue
            pub, year, pos = r["eli"].split("/")
            md = root / pub / year / f"{pub}-{year}-{pos}.md"
            if not md.exists():
                continue
            c = closing_date(body(md.read_text(encoding="utf-8")))
            ann = r["announcement_date"]
            verdict = "brak daty w tekście" if not c else "zgodna" if c[0] == ann else "inna"
            counts[verdict] = counts.get(verdict, 0) + 1
            w.writerow([r["eli"], ann, c[0] if c else "", verdict, c[1] if c else "", r["title"][:150]])
    print(sum(counts.values()), "aktów bez daty w tytule (bez umów):", ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))


if __name__ == "__main__":
    main()
