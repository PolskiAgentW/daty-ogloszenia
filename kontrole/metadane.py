"""Kontrola 4: czy tytuł w API ELI (data i numer aktu) zgadza się z nagłówkiem aktu w PDF-ie.

Nagłówek = tekst strony 1–2 po linii „Poz. N” (N = pozycja z API) do pierwszej linii treści („Na podstawie”, „§ 1”,
„Art. 1”, „Podaje się” …). Z tytułu i z nagłówka brana jest pierwsza data „z dnia …” i numer „nr …” (w nagłówku
tylko numer stojący przy dacie aktu).
  ok            data i numer zgodne (albo brak jednego z nich po którejś stronie)
  bez-naglowka  nie znaleziono w nagłówku ani daty, ani numeru (nie sprawdzone)
  DATA / NR / DATA+NR  różnica; data liczy się tylko przy różnicy do 400 dni (większa to zwykle data przywołanego aktu)
Typowy prawdziwy przypadek: rekord ma tytuł, numer i datę sąsiedniego rekordu (kolumna ten_sam_tytul_co pokazuje
rekordy z identycznym tytułem w roczniku). Różnicę trzeba obejrzeć w PDF-ie; trafność w README.md. Od 2012 r. każdy akt
ma osobny PDF; wcześniej PDF obejmuje kilka aktów i kodowanie bywa inne, więc lata < 2012 są pomijane bez
--takze-przed-2012.

    python3 metadane.py --pub MP --lata 2012-2026 WYNIK.csv"""
import argparse
import csv
import datetime
import re
import sys
from collections import Counter, defaultdict

from wspolne import cached_acts, pdftext, years

MONTHS = {'stycznia': 1, 'lutego': 2, 'marca': 3, 'kwietnia': 4, 'maja': 5, 'czerwca': 6, 'lipca': 7,
          'sierpnia': 8, 'września': 9, 'wrzesnia': 9, 'października': 10, 'pazdziernika': 10,
          'listopada': 11, 'grudnia': 12}
MON = '|'.join(sorted(MONTHS, key=len, reverse=True))
DATE = r'([0-3]?[0-9lIi])\s*(?:-?go)?\s+(' + MON + r')\s+((?:1[89]|20)[0-9]{2})'
RX_DATE = re.compile(r'z\s*d\s*n\s*i\s*a\s+' + DATE, re.I)
RX_NR = re.compile(r'\b[Nn]\s*[Rr]\s+(?:[Rr][Ee][Jj]\s*\.\s*)?([0-9][0-9 ./\-]*[0-9]|[0-9])')
BODY = re.compile(r'^\s*(Na podstawie|§\s*1|Art\.\s*1|Podaje się|W związku z|Działając na podstawie)')


def first_date(s: str) -> str:
    m = RX_DATE.search(s)
    if not m:
        return ''
    try:
        d = int(re.sub(r'[lIi]', '1', m.group(1)))
    except ValueError:
        return ''
    mo = MONTHS.get(m.group(2).lower())
    return f'{int(m.group(3)):04d}-{mo:02d}-{d:02d}' if mo and 1 <= d <= 31 else ''


def first_nr(s: str, near_date: bool = False) -> str:
    if near_date:  # nagłówek: numer przy dacie aktu („z dnia … r. nr …” / „NR … z dnia”)
        m = RX_DATE.search(s)
        if not m:
            return ''
        s = s[max(0, m.start() - 60):m.end() + 40]
    m = RX_NR.search(s)
    return re.sub(r'\s+', '', m.group(1)) if m else ''


def days(a: str, b: str) -> int:
    try:
        return abs((datetime.date.fromisoformat(a) - datetime.date.fromisoformat(b)).days)
    except ValueError:  # np. „30 lutego” z błędu OCR
        return 10 ** 6


def norm(s: str) -> str:
    s = s.lower().replace('„', '').replace('”', '').replace('"', '').replace('–', '-')
    s = re.sub(r'(?<=\w)\s*\d\)', '', s)  # odnośniki „TECHNOLOGII 1)”
    return re.sub(r'\s+', '', s)


def heading(pdf, pos: int) -> str:
    lines = [ln.strip() for ln in pdftext(pdf, last=2).splitlines() if ln.strip()]
    start = 0
    for i, ln in enumerate(lines[:80]):
        if re.fullmatch(r'Poz\.\s*%d' % pos, ln) or ln == str(pos):
            start = i + 1
            break
    out = []
    for ln in lines[start:start + 25]:
        if BODY.match(ln):
            break
        if not re.fullmatch(r'\d+', ln):
            out.append(ln)
    return ' '.join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--pub', required=True, choices=('DU', 'MP'))
    ap.add_argument('--lata', required=True)
    ap.add_argument('wynik')
    ap.add_argument('--takze-przed-2012', action='store_true')
    a = ap.parse_args()
    yrs = [y for y in years(a.lata) if y >= 2012 or a.takze_przed_2012]
    groups = defaultdict(list)
    for meta, pdf in cached_acts(a.pub, yrs):
        groups[(meta['year'], (meta.get('title') or '').strip())].append((meta, pdf))
    c = Counter()
    with open(a.wynik, 'w', newline='', encoding='utf-8') as fo:
        w = csv.writer(fo)
        w.writerow(['eli', 'wynik', 'data_w_tytule', 'data_w_naglowku', 'nr_w_tytule', 'nr_w_naglowku',
                    'ten_sam_tytul_co', 'tytul', 'naglowek_pdf'])
        for (_, t), recs in sorted(groups.items()):
            for meta, pdf in recs:
                h = heading(pdf, meta['pos'])
                td, hd = first_date(t), first_date(h)
                tn, hn = first_nr(t), first_nr(h, near_date=True)
                bad = []
                if td and hd and td != hd and days(td, hd) <= 400:
                    bad.append('DATA')
                if tn and hn and norm(tn) != norm(hn):
                    bad.append('NR')
                v = '+'.join(bad) if bad else ('ok' if (hd or hn) else 'bez-naglowka')
                c[v] += 1
                w.writerow([meta['ELI'], v, td, hd, tn, hn, ' '.join(m['ELI'] for m, _ in recs if m is not meta),
                            t[:200], h[:300]])
    print(a.pub, sum(c.values()), 'PDF:', dict(c), file=sys.stderr)


if __name__ == '__main__':
    main()
