"""Basit tarama (screener).

Her hisse için günlük veriden birkaç temel metrik hesaplar
(son fiyat, günlük %, RSI, 50/200 gün ortalamaya göre konum) ve
kullanıcının seçtiği kurallara göre filtreler.

Bu bir tavsiye üreticisi değildir: sadece kullanıcının tanımladığı
teknik koşulları sağlayan hisseleri listeler.
"""
from __future__ import annotations

import pandas as pd

from . import indicators as ind


def compute_metrics(symbol: str, df: pd.DataFrame) -> dict | None:
    """Tek hisse için tarama metriklerini hesaplar."""
    if df is None or df.empty or len(df) < 30:
        return None
    close = df["Close"].dropna()
    if len(close) < 30:
        return None

    rsi_series = ind.rsi(close, 14)
    sma50 = ind.sma(close, 50)
    sma200 = ind.sma(close, 200)

    last = float(close.iloc[-1])
    prev = float(close.iloc[-2]) if len(close) >= 2 else last
    day_pct = (last / prev - 1.0) * 100.0 if prev else 0.0

    # haftalık (~5 işlem günü) değişim
    wk_pct = None
    if len(close) >= 6:
        wk_pct = (last / float(close.iloc[-6]) - 1.0) * 100.0

    rsi_val = float(rsi_series.iloc[-1]) if rsi_series.notna().iloc[-1] else None
    sma50_val = float(sma50.iloc[-1]) if sma50.notna().iloc[-1] else None
    sma200_val = float(sma200.iloc[-1]) if sma200.notna().iloc[-1] else None

    return {
        "Kod": symbol.replace(".IS", ""),
        "Fiyat": round(last, 2),
        "Günlük %": round(day_pct, 2),
        "Haftalık %": round(wk_pct, 2) if wk_pct is not None else None,
        "RSI(14)": round(rsi_val, 1) if rsi_val is not None else None,
        "50>200 (Altın)": (
            bool(sma50_val > sma200_val)
            if (sma50_val is not None and sma200_val is not None)
            else None
        ),
        "Fiyat>50g": (
            bool(last > sma50_val) if sma50_val is not None else None
        ),
        "_symbol": symbol,
    }


def build_table(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Bir {sembol: df} sözlüğünden tarama tablosu üretir."""
    rows = []
    for sym, df in data.items():
        m = compute_metrics(sym, df)
        if m:
            rows.append(m)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def apply_filters(
    table: pd.DataFrame,
    *,
    rsi_max: float | None = None,
    rsi_min: float | None = None,
    only_golden_cross: bool = False,
    only_above_sma50: bool = False,
    min_day_pct: float | None = None,
) -> pd.DataFrame:
    """Tarama tablosuna kullanıcı kurallarını uygular."""
    if table.empty:
        return table
    out = table.copy()
    if rsi_max is not None:
        out = out[out["RSI(14)"].notna() & (out["RSI(14)"] <= rsi_max)]
    if rsi_min is not None:
        out = out[out["RSI(14)"].notna() & (out["RSI(14)"] >= rsi_min)]
    if only_golden_cross:
        out = out[out["50>200 (Altın)"] == True]  # noqa: E712
    if only_above_sma50:
        out = out[out["Fiyat>50g"] == True]  # noqa: E712
    if min_day_pct is not None:
        out = out[out["Günlük %"] >= min_day_pct]
    return out
