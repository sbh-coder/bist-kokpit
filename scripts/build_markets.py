# -*- coding: utf-8 -*-
"""BIST pazar sınıflandırmasını (Yıldız + Ana Pazar) üretir → src/markets.py.

Kaynak: KAP "Pazarlar" sayfası (https://www.kap.org.tr/tr/Pazarlar). Bu sayfa
tüm pazarları, her pazarın şirket listesiyle birlikte TEK istekte döndürür
(marketName + marketDetailContentList). Böylece 800 ayrı istek/throttle derdi
olmadan bütün Yıldız+Ana hisseleri alınır.

Yenilemek için:  python scripts/build_markets.py
"""
import re
import json
import os
import httpx

URL = "https://www.kap.org.tr/tr/Pazarlar"
OUT = os.path.join(os.path.dirname(__file__), "..", "src", "markets.py")
HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "tr",
    "Referer": "https://www.kap.org.tr/tr/bist-sirketler",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
}


def fetch_markets() -> dict[str, dict[str, str]]:
    html = httpx.get(URL, headers=HEADERS, timeout=30, follow_redirects=True).text
    text = html.replace('\\"', '"')
    # Her pazar: "marketName":"...","marketDetailContentList":[{"stockCode":"..","title":".."}]
    names = [(m.start(), m.group(1)) for m in re.finditer(r'"marketName":"([^"]+)"', text)]
    groups: dict[str, dict[str, str]] = {}
    for i, (pos, name) in enumerate(names):
        end = names[i + 1][0] if i + 1 < len(names) else len(text)
        seg = text[pos:end]
        g = groups.setdefault(name, {})
        for code, title in re.findall(r'"stockCode":"([^"]+)","title":"([^"]*)"', seg):
            g[code] = title
    return groups


def main() -> None:
    groups = fetch_markets()
    yildiz = {f"{c}.IS": t for c, t in groups.get("YILDIZ PAZAR", {}).items()}
    ana = {f"{c}.IS": t for c, t in groups.get("ANA PAZAR", {}).items()}
    if len(yildiz) + len(ana) < 100:
        raise SystemExit(f"Beklenenden az hisse ({len(yildiz)}+{len(ana)}); yazılmadı.")

    header = (
        '"""BIST pazar sınıflandırması — YILDIZ PAZAR + ANA PAZAR.\n\n'
        "Kaynak: KAP Pazarlar sayfası (scripts/build_markets.py). Anlık görüntü: 2026-08-16.\n"
        "Pazar atamaları zaman zaman değişir; yenilemek için scripts/build_markets.py çalıştırın.\n"
        '"""\n\n'
    )
    body = (
        "YILDIZ_PAZAR = " + json.dumps(dict(sorted(yildiz.items())), ensure_ascii=False, indent=4) + "\n\n"
        "ANA_PAZAR = " + json.dumps(dict(sorted(ana.items())), ensure_ascii=False, indent=4) + "\n\n"
        "# Yıldız + Ana Pazar (izleme evreni)\n"
        "YILDIZ_ANA = {**YILDIZ_PAZAR, **ANA_PAZAR}\n"
    )
    with open(os.path.abspath(OUT), "w", encoding="utf-8") as f:
        f.write(header + body)
    print(f"YAZILDI {os.path.abspath(OUT)} — YILDIZ {len(yildiz)} + ANA {len(ana)} = {len(yildiz)+len(ana)} hisse")


if __name__ == "__main__":
    main()
