"""TradingView taraması — borsapy'nin TradingView screener'ı (sunucu-taraflı).

borsapy.scan(universe, condition, interval, limit) filtrelemeyi TradingView
sunucusunda yapar → tüm evreni saniyeler içinde tarar (yfinance'i tek tek
çekmeye gerek yok). Lazy + korumalı import: borsapy yoksa/patlarsa uygulama çökmez.

Veriler ~15 dk gecikmelidir; sonuçlar mekanik kurallardır, yatırım tavsiyesi değildir.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

# Görünen ad -> TradingView koşulu
TV_PRESETS: dict[str, str] = {
    "RSI Aşırı Satım (<30)": "rsi < 30",
    "RSI Aşırı Alım (>70)": "rsi > 70",
    "Fiyat 50 Ortalama Üstünde": "close > sma_50",
    "Fiyat 200 Ortalama Üstünde": "close > sma_200",
    "Altın Dizilim (50>200)": "sma_50 > sma_200",
    "Altın Çapraz — yeni kesişim": "sma_50 crosses_above sma_200",
    "Ölüm Çaprazı — yeni kesişim": "sma_50 crosses_below sma_200",
    "MACD Al (yukarı kesişim)": "macd crosses_above signal",
    "MACD Sat (aşağı kesişim)": "macd crosses_below signal",
    "MACD > Sinyal": "macd > signal",
    "Bollinger Alt Altında (aşırı satım)": "close < bb_lower",
    "Bollinger Üst Üstünde (kırılım)": "close > bb_upper",
    "ADX Güçlü Trend (>25)": "adx > 25",
    "Stochastic Aşırı Satım (<20)": "stoch_k < 20",
    "Stochastic Aşırı Alım (>80)": "stoch_k > 80",
    "Yüksek Hacim (>10M)": "volume > 10M",
    "Sert Yükseliş (günlük >%5)": "change_percent > 5",
    "Sert Düşüş (günlük <-%5)": "change_percent < -5",
    "Aşırı Satım + Yükseliş Trendi": "rsi < 35 and close > sma_200",
    "MACD Al + RSI<60": "macd crosses_above signal and rsi < 60",
}

# Uygulamanın zaman dilimi etiketi -> TradingView aralığı
TV_INTERVALS: dict[str, str] = {
    "15 dakika": "15m",
    "1 saat": "1h",
    "4 saat": "4h",
    "1 gün": "1d",
    "1 hafta": "1W",
    "1 ay": "1M",
}

_RENAME = {
    "symbol": "Kod", "name": "Ad", "close": "Fiyat", "change": "Değişim %",
    "rsi": "RSI", "volume": "Hacim", "macd": "MACD", "macd_signal": "Sinyal",
    "sma20": "SMA20", "sma50": "SMA50", "sma200": "SMA200", "ema20": "EMA20",
    "adx": "ADX", "stoch_k": "StochK", "stoch_d": "StochD",
    "bb_lower": "BB Alt", "bb_upper": "BB Üst", "histogram": "Histogram",
}


def is_available() -> bool:
    try:
        import borsapy  # noqa: F401
        return True
    except Exception:
        return False


@st.cache_data(ttl=600, show_spinner=False)
def run(universe, condition: str, interval: str = "1d", limit: int = 600) -> pd.DataFrame:
    """TradingView taraması. universe: index str ("XU100") ya da kod tuple'ı.

    Çağıran taraf hata durumunu try/except ile ele alır.
    """
    import borsapy as bp

    uni = list(universe) if isinstance(universe, tuple) else universe
    df = bp.scan(uni, condition, interval=interval, limit=limit)
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.drop(columns=["market_cap", "conditions_met"], errors="ignore")
    df = df.rename(columns=_RENAME)
    front = [c for c in ["Kod", "Ad", "Fiyat", "Değişim %"] if c in df.columns]
    rest = [c for c in df.columns if c not in front]
    df = df[front + rest]
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]):
            df[c] = df[c].round(2)
    return df.reset_index(drop=True)
