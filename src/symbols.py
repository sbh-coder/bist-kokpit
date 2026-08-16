"""BIST hisse listesi (Yahoo Finance formatı: TICKER.IS).

Bu, likit ve bilinen ~40 BIST hissesinden oluşan başlangıç listesidir.
Kullanıcı arayüzde istediği başka bir kodu da (örn. "SOKM.IS") elle ekleyebilir.
İleride borsapy ile BIST'in TAM listesini dinamik çekebiliriz (README'ye bakın).
"""
from __future__ import annotations

# {Yahoo kodu: "Görünen ad"}
BIST_SYMBOLS: dict[str, str] = {
    "THYAO.IS": "Türk Hava Yolları",
    "GARAN.IS": "Garanti BBVA",
    "AKBNK.IS": "Akbank",
    "ISCTR.IS": "İş Bankası (C)",
    "YKBNK.IS": "Yapı Kredi",
    "SISE.IS": "Şişecam",
    "EREGL.IS": "Ereğli Demir Çelik",
    "KCHOL.IS": "Koç Holding",
    "SAHOL.IS": "Sabancı Holding",
    "BIMAS.IS": "BİM",
    "ASELS.IS": "Aselsan",
    "TUPRS.IS": "Tüpraş",
    "FROTO.IS": "Ford Otosan",
    "TOASO.IS": "Tofaş",
    "PGSUS.IS": "Pegasus",
    "TCELL.IS": "Turkcell",
    "TTKOM.IS": "Türk Telekom",
    "KOZAL.IS": "Koza Altın",
    "KOZAA.IS": "Koza Anadolu",
    "PETKM.IS": "Petkim",
    "TAVHL.IS": "TAV Havalimanları",
    "HEKTS.IS": "Hektaş",
    "SASA.IS": "Sasa Polyester",
    "KRDMD.IS": "Kardemir (D)",
    "VESTL.IS": "Vestel",
    "ARCLK.IS": "Arçelik",
    "ENKAI.IS": "Enka İnşaat",
    "GUBRF.IS": "Gübre Fabrikaları",
    "OYAKC.IS": "Oyak Çimento",
    "EKGYO.IS": "Emlak Konut GYO",
    "MGROS.IS": "Migros",
    "SOKM.IS": "Şok Marketler",
    "DOHOL.IS": "Doğan Holding",
    "ODAS.IS": "Odaş Elektrik",
    "ALARK.IS": "Alarko Holding",
    "TKFEN.IS": "Tekfen Holding",
    "KONTR.IS": "Kontrolmatik",
    "SMRTG.IS": "Smart Güneş",
    "ASTOR.IS": "Astor Enerji",
}

# Varsayılan izleme listesi (ilk açılışta gösterilecek)
DEFAULT_WATCHLIST: list[str] = [
    "THYAO.IS",
    "GARAN.IS",
    "ASELS.IS",
    "EREGL.IS",
    "BIMAS.IS",
    "TUPRS.IS",
    "KCHOL.IS",
    "SISE.IS",
]


# Genişletilebilir isim defteri. BIST_SYMBOLS "öne çıkan ~40 hisse" olarak
# kalır (teknik tarama evreni). borsapy varsa tüm BIST (797) buraya EKLENİR,
# böylece izleme listesine istediğin herhangi bir hisseyi seçebilirsin.
ALL_NAMES: dict[str, str] = dict(BIST_SYMBOLS)


def register(extra: dict[str, str]) -> None:
    """borsapy'den gelen tam BIST evrenini etiket defterine ekler (curated adları korur)."""
    for k, v in extra.items():
        ALL_NAMES.setdefault(k, v)


def label(symbol: str) -> str:
    """Kod -> 'KOD — Ad' etiketi."""
    name = ALL_NAMES.get(symbol)
    short = symbol.replace(".IS", "")
    return f"{short} — {name}" if name and name != "—" else short
