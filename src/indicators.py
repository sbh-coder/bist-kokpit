"""Teknik göstergeler — saf pandas/numpy, hiçbir C bağımlılığı yok.

Not: Bunlar bilinen, standart göstergelerdir. Ürettikleri "sinyal" bir
yatırım tavsiyesi değil, kullanıcının seçtiği kuralın mekanik sonucudur.
Daha zengin gösterge seti isterseniz `pandas-ta-classic` veya `TA-Lib`
buraya kolayca eklenebilir (README'ye bakın).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    """Basit Hareketli Ortalama."""
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Üstel Hareketli Ortalama."""
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Göreceli Güç Endeksi (Wilder yöntemi)."""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    # Wilder yumuşatması = EMA with alpha = 1/period
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    # avg_loss == 0 (hiç düşüş yok) -> RSI 100
    out = out.where(avg_loss != 0.0, 100.0)
    return out


def macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
    """MACD çizgisi, sinyal çizgisi ve histogram."""
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame(
        {"macd": macd_line, "signal": signal_line, "hist": hist}
    )


def bollinger(series: pd.Series, period: int = 20, k: float = 2.0) -> pd.DataFrame:
    """Bollinger Bantları."""
    mid = sma(series, period)
    std = series.rolling(window=period, min_periods=period).std()
    upper = mid + k * std
    lower = mid - k * std
    return pd.DataFrame({"mid": mid, "upper": upper, "lower": lower})


def add_indicators(
    df: pd.DataFrame,
    *,
    sma_fast: int = 50,
    sma_slow: int = 200,
    rsi_period: int = 14,
) -> pd.DataFrame:
    """Bir OHLC tablosuna standart gösterge kolonlarını ekler."""
    out = df.copy()
    close = out["Close"]
    out[f"SMA{sma_fast}"] = sma(close, sma_fast)
    out[f"SMA{sma_slow}"] = sma(close, sma_slow)
    out["EMA20"] = ema(close, 20)
    out["RSI"] = rsi(close, rsi_period)
    macd_df = macd(close)
    out["MACD"] = macd_df["macd"]
    out["MACD_signal"] = macd_df["signal"]
    out["MACD_hist"] = macd_df["hist"]
    return out
