"""Hazır (preset) teknik taramalar — en sık kullanılanlar.

Her tarama, kendisine verilen OHLCV tablosunun BARLARI üzerinden hesaplanır;
bu yüzden herhangi bir zaman diliminde (15dk, 1s, 4s, 1g, 1h, 1a) çalışır.
Etiketler "gün/hafta" yerine "bar/ortalama" gibi zaman-dilimi-nötr ifadeler
kullanır (örn. 252 bar = günlük grafikte ~1 yıl).

Her tarama fonksiyonu bir hisse için (eşleşti_mi: bool, kısa_açıklama: str)
döndürür. Bunlar bilinen teknik kurallardır; sonuç yatırım tavsiyesi DEĞİLDİR.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import indicators as ind


# --------------------------------------------------------------------------
# Yardımcılar
# --------------------------------------------------------------------------
def _last(series: pd.Series) -> float:
    s = series.dropna()
    return float(s.iloc[-1]) if len(s) else float("nan")


def _crossed_up(a: pd.Series, b: pd.Series, within: int = 2) -> bool:
    """a, b'yi son `within` bar içinde AŞAĞIDAN YUKARI kesti mi?"""
    d = (a - b).dropna()
    if len(d) < within + 1:
        return False
    for i in range(1, within + 1):
        if d.iloc[-i] > 0 and d.iloc[-i - 1] <= 0:
            return True
    return False


def _crossed_down(a: pd.Series, b: pd.Series, within: int = 2) -> bool:
    """a, b'yi son `within` bar içinde YUKARIDAN AŞAĞI kesti mi?"""
    d = (a - b).dropna()
    if len(d) < within + 1:
        return False
    for i in range(1, within + 1):
        if d.iloc[-i] < 0 and d.iloc[-i - 1] >= 0:
            return True
    return False


def _prep(df: pd.DataFrame) -> dict:
    """Bir hisse için gerekli tüm gösterge serilerini bir kez hesaplar."""
    c = df["Close"]
    macd = ind.macd(c)
    boll = ind.bollinger(c, 20, 2.0)
    vol = df["Volume"] if "Volume" in df else pd.Series(index=df.index, dtype=float)
    return {
        "c": c, "o": df["Open"], "h": df["High"], "l": df["Low"], "v": vol,
        "sma20": ind.sma(c, 20), "sma50": ind.sma(c, 50), "sma200": ind.sma(c, 200),
        "rsi": ind.rsi(c, 14),
        "macd": macd["macd"], "signal": macd["signal"],
        "bu": boll["upper"], "bl": boll["lower"], "bm": boll["mid"],
    }


# --------------------------------------------------------------------------
# Taramalar: her biri (prep) -> (bool, açıklama)
# --------------------------------------------------------------------------
def _golden(x):
    return _last(x["sma50"]) > _last(x["sma200"]), "50 ort. > 200 ort."


def _new_golden(x):
    return _crossed_up(x["sma50"], x["sma200"], within=5), "son 5 barda kesişti"


def _death(x):
    return _last(x["sma50"]) < _last(x["sma200"]), "50 ort. < 200 ort."


def _new_death(x):
    return _crossed_down(x["sma50"], x["sma200"], within=5), "son 5 barda kesişti"


def _perfect(x):
    c, s20, s50, s200 = _last(x["c"]), _last(x["sma20"]), _last(x["sma50"]), _last(x["sma200"])
    return (c > s20 > s50 > s200), "Fiyat>20>50>200 ort."


def _above200(x):
    return _last(x["c"]) > _last(x["sma200"]), "fiyat 200 ort. üstünde"


def _above50(x):
    return _last(x["c"]) > _last(x["sma50"]), "fiyat 50 ort. üstünde"


def _rsi_os(x):
    r = _last(x["rsi"])
    return r < 30, f"RSI {r:.0f}"


def _rsi_ob(x):
    r = _last(x["rsi"])
    return r > 70, f"RSI {r:.0f}"


def _rsi_cross50(x):
    fifty = pd.Series(50.0, index=x["rsi"].index)
    return _crossed_up(x["rsi"], fifty, within=2), "RSI 50'yi yukarı kesti"


def _macd_buy(x):
    return _crossed_up(x["macd"], x["signal"], within=2), "MACD yukarı kesişim"


def _macd_sell(x):
    return _crossed_down(x["macd"], x["signal"], within=2), "MACD aşağı kesişim"


def _macd_pos(x):
    return _last(x["macd"]) > 0, "MACD sıfır üstü"


def _boll_lower(x):
    c, bl = _last(x["c"]), _last(x["bl"])
    return c <= bl, "alt banda değdi"


def _boll_break(x):
    c, bu = _last(x["c"]), _last(x["bu"])
    return c >= bu, "üst bandı kırdı"


def _boll_squeeze(x):
    width = ((x["bu"] - x["bl"]) / x["bm"]).dropna()
    if len(width) < 60:
        return False, ""
    ok = width.iloc[-1] <= width.tail(120).quantile(0.15)
    return bool(ok), "bantlar sıkıştı"


def _high_range(x):
    c, hi = _last(x["c"]), x["h"].tail(252).max()
    if not (hi > 0):
        return False, ""
    return c >= 0.97 * hi, f"zirveye %{(1 - c / hi) * 100:.1f}"


def _low_range(x):
    c, lo = _last(x["c"]), x["l"].tail(252).min()
    if not (lo > 0):
        return False, ""
    return c <= 1.03 * lo, f"dibe %{(c / lo - 1) * 100:.1f}"


def _donchian_high(x):
    c = _last(x["c"])
    prior = x["h"].iloc[-21:-1].max()
    return c > prior, "20 bar zirvesini aştı"


def _donchian_low(x):
    c = _last(x["c"])
    prior = x["l"].iloc[-21:-1].min()
    return c < prior, "20 bar dibini kırdı"


def _vol_spike(x):
    v = x["v"].dropna()
    if len(v) < 21 or v.iloc[-1] == 0:
        return False, ""
    avg = v.iloc[-21:-1].mean()
    if not (avg > 0):
        return False, ""
    ratio = v.iloc[-1] / avg
    return ratio >= 2.0, f"hacim {ratio:.1f}x ortalama"


def _strong_up(x):
    c = x["c"].dropna()
    if len(c) < 2:
        return False, ""
    ch = (c.iloc[-1] / c.iloc[-2] - 1) * 100
    return ch >= 5.0, f"son bar +%{ch:.1f}"


def _strong_down(x):
    c = x["c"].dropna()
    if len(c) < 2:
        return False, ""
    ch = (c.iloc[-1] / c.iloc[-2] - 1) * 100
    return ch <= -5.0, f"son bar %{ch:.1f}"


# --- Mum (candlestick) formasyonları — son bar(lar)dan hesaplanır ---
def _ohlc(x, i):
    return (
        float(x["o"].iloc[i]), float(x["h"].iloc[i]),
        float(x["l"].iloc[i]), float(x["c"].iloc[i]),
    )


def _doji(x):
    o, h, l, c = _ohlc(x, -1)
    rng = h - l
    return (rng > 0 and abs(c - o) <= 0.1 * rng), "doji (kararsızlık)"


def _hammer(x):
    o, h, l, c = _ohlc(x, -1)
    rng = h - l
    if rng <= 0:
        return False, ""
    body = abs(c - o)
    lower = min(o, c) - l
    upper = h - max(o, c)
    return (body > 0 and lower >= 2 * body and upper <= body), "çekiç (boğa dönüş)"


def _shooting_star(x):
    o, h, l, c = _ohlc(x, -1)
    rng = h - l
    if rng <= 0:
        return False, ""
    body = abs(c - o)
    lower = min(o, c) - l
    upper = h - max(o, c)
    return (body > 0 and upper >= 2 * body and lower <= body), "kayan yıldız (ayı dönüş)"


def _bull_engulf(x):
    o1, _, _, c1 = _ohlc(x, -2)
    o0, _, _, c0 = _ohlc(x, -1)
    return (c1 < o1 and c0 > o0 and o0 <= c1 and c0 >= o1), "yutan boğa"


def _bear_engulf(x):
    o1, _, _, c1 = _ohlc(x, -2)
    o0, _, _, c0 = _ohlc(x, -1)
    return (c1 > o1 and c0 < o0 and o0 >= c1 and c0 <= o1), "yutan ayı"


def _morning_star(x):
    o2, _, _, c2 = _ohlc(x, -3)
    o1, _, _, c1 = _ohlc(x, -2)
    o0, _, _, c0 = _ohlc(x, -1)
    b2 = abs(c2 - o2)
    return (
        c2 < o2 and b2 > 0 and abs(c1 - o1) <= 0.5 * b2
        and c0 > o0 and c0 > (o2 + c2) / 2
    ), "sabah yıldızı"


def _evening_star(x):
    o2, _, _, c2 = _ohlc(x, -3)
    o1, _, _, c1 = _ohlc(x, -2)
    o0, _, _, c0 = _ohlc(x, -1)
    b2 = abs(c2 - o2)
    return (
        c2 > o2 and b2 > 0 and abs(c1 - o1) <= 0.5 * b2
        and c0 < o0 and c0 < (o2 + c2) / 2
    ), "akşam yıldızı"


def _marubozu(x):
    o, h, l, c = _ohlc(x, -1)
    rng = h - l
    if rng <= 0:
        return False, ""
    return abs(c - o) >= 0.9 * rng, "marubozu (%s)" % ("boğa" if c > o else "ayı")


# {Görünen ad: (açıklama, fonksiyon)}. "bar" = seçilen zaman diliminin çubuğu.
SCANS: dict[str, tuple[str, object]] = {
    # Trend & Ortalamalar
    "Altın Çapraz (50>200)": ("50 ortalama 200 ortalamanın üstünde — yükseliş eğilimi.", _golden),
    "Yeni Altın Çapraz (son 5 bar)": ("50 ortalama, 200 ortalamayı son 5 barda yukarı kesti — taze sinyal.", _new_golden),
    "Ölüm Çaprazı (50<200)": ("50 ortalama 200 ortalamanın altında — düşüş eğilimi.", _death),
    "Yeni Ölüm Çaprazı (son 5 bar)": ("50 ortalama, 200 ortalamayı son 5 barda aşağı kesti.", _new_death),
    "Kusursuz Yükseliş Dizilimi": ("Fiyat > 20 > 50 > 200 ortalama — güçlü, düzenli yükseliş.", _perfect),
    "Fiyat 200 Ortalama Üstünde": ("Fiyat 200 barlık ortalamanın üzerinde.", _above200),
    "Fiyat 50 Ortalama Üstünde": ("Fiyat 50 barlık ortalamanın üzerinde.", _above50),
    # RSI
    "RSI Aşırı Satım (<30)": ("RSI 30'un altında — aşırı satım bölgesi.", _rsi_os),
    "RSI Aşırı Alım (>70)": ("RSI 70'in üstünde — aşırı alım bölgesi.", _rsi_ob),
    "RSI 50'yi Yukarı Kesti": ("RSI son 2 barda 50 çizgisini yukarı geçti — momentum dönüşü.", _rsi_cross50),
    # MACD
    "MACD Al Sinyali (yukarı kesişim)": ("MACD çizgisi sinyal çizgisini son 2 barda yukarı kesti.", _macd_buy),
    "MACD Sat Sinyali (aşağı kesişim)": ("MACD çizgisi sinyal çizgisini son 2 barda aşağı kesti.", _macd_sell),
    "MACD Sıfırın Üstünde": ("MACD çizgisi sıfırın üzerinde — pozitif momentum.", _macd_pos),
    # Bollinger
    "Bollinger Alt Bandı (dip test)": ("Fiyat alt Bollinger bandına değdi / altına indi.", _boll_lower),
    "Bollinger Üst Kırılımı": ("Fiyat üst Bollinger bandını kırdı — güçlü hareket.", _boll_break),
    "Bollinger Sıkışması (squeeze)": ("Bantlar son dönemin en darında — sert hareket adayı.", _boll_squeeze),
    # Kırılım & aralık
    "Uzun Vade Zirvesine Yakın (252 bar)": ("Fiyat son 252 barın (günlükte ~1 yıl) zirvesine %3 mesafede.", _high_range),
    "Uzun Vade Dibine Yakın (252 bar)": ("Fiyat son 252 barın (günlükte ~1 yıl) dibine %3 mesafede.", _low_range),
    "20 Bar Zirve Kırılımı (Donchian)": ("Fiyat son 20 barın en yükseğini aştı — kırılım.", _donchian_high),
    "20 Bar Dip Kırılımı": ("Fiyat son 20 barın en düşüğünü kırdı.", _donchian_low),
    # Hacim & sert hareket
    "Hacim Patlaması (2x ortalama)": ("Son bar hacmi, 20 bar ortalamasının 2 katından fazla.", _vol_spike),
    "Sert Yükseliş (son bar ≥ %5)": ("Son bar değişimi +%5 ve üzeri.", _strong_up),
    "Sert Düşüş (son bar ≤ -%5)": ("Son bar değişimi -%5 ve altı.", _strong_down),
    # Mum (candlestick) formasyonları
    "Mum: Doji": ("Açılış ≈ kapanış — kararsızlık/dönüş adayı.", _doji),
    "Mum: Çekiç (Hammer)": ("Küçük gövde + uzun alt fitil — boğa dönüş sinyali.", _hammer),
    "Mum: Kayan Yıldız": ("Küçük gövde + uzun üst fitil — ayı dönüş sinyali.", _shooting_star),
    "Mum: Yutan Boğa": ("Yükselen mum, önceki düşen mumu yutuyor — boğa.", _bull_engulf),
    "Mum: Yutan Ayı": ("Düşen mum, önceki yükselen mumu yutuyor — ayı.", _bear_engulf),
    "Mum: Sabah Yıldızı": ("3 mumluk boğa dönüş formasyonu.", _morning_star),
    "Mum: Akşam Yıldızı": ("3 mumluk ayı dönüş formasyonu.", _evening_star),
    "Mum: Marubozu": ("Fitilsiz güçlü gövde — güçlü yön.", _marubozu),
}


def run_scan(name: str, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Seçili taramayı bir {sembol: df} sözlüğüne uygular, eşleşenleri döndürür."""
    if name not in SCANS:
        return pd.DataFrame()
    _, fn = SCANS[name]
    rows = []
    for sym, df in data.items():
        if df is None or df.empty or len(df) < 30:
            continue
        try:
            matched, detail = fn(_prep(df))
        except Exception:  # noqa: BLE001 - tek hisse patlarsa taramayı durdurma
            continue
        if not matched:
            continue
        c = df["Close"].dropna()
        last = float(c.iloc[-1])
        prev = float(c.iloc[-2]) if len(c) > 1 else last
        chg = (last / prev - 1.0) * 100.0 if prev else 0.0
        rsi_val = _last(ind.rsi(df["Close"], 14))
        rows.append(
            {
                "Kod": sym.replace(".IS", ""),
                "Fiyat": round(last, 2),
                "Değişim %": round(chg, 2),
                "RSI(14)": round(rsi_val, 1) if rsi_val == rsi_val else None,
                "Detay": detail,
            }
        )
    return pd.DataFrame(rows)


def run_scans(names: list[str], data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Birden çok taramayı AYNI ANDA çalıştırır; hisse bazında ✓ matrisi döndürür.

    Satırlar = en az bir taramaya uyan hisseler (en çok eşleşen en üstte).
    Sütunlar = Kod, Fiyat, Değişim %, Eşleşme (adet) + her tarama için ✓/boş.
    Her hisse için göstergeler yalnızca BİR kez hesaplanır (verimli).
    """
    names = [n for n in names if n in SCANS]
    if not names:
        return pd.DataFrame()

    # Sütun başlıklarını kısalt (parantezi at); çakışma olursa tam adı kullan.
    labels = {n: n.split(" (")[0] for n in names}
    if len(set(labels.values())) < len(labels):
        labels = {n: n for n in names}

    rows = []
    for sym, df in data.items():
        if df is None or df.empty or len(df) < 30:
            continue
        try:
            x = _prep(df)
        except Exception:  # noqa: BLE001
            continue
        cells = {}
        matched = 0
        for n in names:
            _, fn = SCANS[n]
            try:
                ok, _ = fn(x)
            except Exception:  # noqa: BLE001
                ok = False
            cells[labels[n]] = "✓" if ok else ""
            matched += 1 if ok else 0
        if matched == 0:
            continue
        c = df["Close"].dropna()
        last = float(c.iloc[-1])
        prev = float(c.iloc[-2]) if len(c) > 1 else last
        chg = (last / prev - 1.0) * 100.0 if prev else 0.0
        row = {
            "Kod": sym.replace(".IS", ""),
            "Fiyat": round(last, 2),
            "Değişim %": round(chg, 2),
            "Eşleşme": matched,
        }
        row.update(cells)
        rows.append(row)

    if not rows:
        return pd.DataFrame()
    return (
        pd.DataFrame(rows)
        .sort_values("Eşleşme", ascending=False)
        .reset_index(drop=True)
    )
