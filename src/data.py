"""Veri katmanı — Yahoo Finance (yfinance) üzerinden BIST verisi.

Önemli gerçekler:
- BIST verisi Yahoo'da ~15 DAKİKA GECİKMELİDİR (canlı değil). Günlük/haftalık
  işlem için bu yeterlidir.
- Kaynak gayriresmîdir; çok sık istek atınca Yahoo geçici olarak engelleyebilir
  (HTTP 429). Bu yüzden her şey `st.cache_data` ile önbelleğe alınır.
- İleride `borsapy` ikinci/yedek kaynak olarak buraya eklenebilir (README).

Tüm fonksiyonlar OHLCV kolonlarını (Open/High/Low/Close/Volume) döndürür.
"""
from __future__ import annotations

import logging

import pandas as pd
import streamlit as st
import yfinance as yf

# yfinance, verisi olmayan/işlem görmeyen sembollerde stderr'e uyarı basar
# (özellikle "Tüm BIST" taramasında çok tekrar eder). Logları temiz tutmak için
# yfinance'in kendi kayıtçısını susturuyoruz — hatalar yine try/except ile ele alınır.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

# Önbellek süresi: veri zaten ~15 dk gecikmeli olduğundan 10 dk önbellek
# hem hızı artırır hem de rate-limit riskini ciddi biçimde düşürür.
_CACHE_TTL = 600


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """yfinance çıktısını standart OHLCV tablosuna indirger."""
    if df is None or df.empty:
        return pd.DataFrame()
    cols = ["Open", "High", "Low", "Close", "Volume"]
    have = [c for c in cols if c in df.columns]
    out = df[have].copy()
    out = out.dropna(how="all")
    # zaman dilimini sadeleştir (grafiklerde tz karışmasın)
    if isinstance(out.index, pd.DatetimeIndex) and out.index.tz is not None:
        out.index = out.index.tz_localize(None)
    return out


@st.cache_data(ttl=_CACHE_TTL, show_spinner=False)
def get_history(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Tek bir hisse için OHLCV geçmişi.

    interval örnekleri: "1d" (günlük), "15m" (15 dakikalık, ~15 dk gecikmeli),
    "1h", "1wk". 15m için Yahoo yalnızca son ~60 günü verir.
    """
    try:
        raw = yf.Ticker(symbol).history(
            period=period, interval=interval, auto_adjust=True
        )
    except Exception as exc:  # noqa: BLE001 - kullanıcıya nazik hata
        st.warning(f"{symbol} verisi çekilemedi: {exc}")
        return pd.DataFrame()
    return _clean(raw)


# Büyük listeler (örn. tüm BIST ~800 hisse) tek istekte çekilirse Yahoo sınır
# koyabilir (HTTP 429). Bu yüzden parça parça çekip birleştiriyoruz.
_CHUNK = 120


def _batch(
    symbols: list[str], interval: str, period: str, resample: str | None = None
) -> dict[str, pd.DataFrame]:
    """Tek bir yf.download çağrısı (bir parça) -> {sym: temiz OHLCV}.

    Bir parça patlarsa boş döner; diğer parçalar etkilenmez (kısmi sonuç alınır).
    """
    if not symbols:
        return {}
    try:
        raw = yf.download(
            list(symbols), period=period, interval=interval, auto_adjust=True,
            group_by="ticker", threads=True, progress=False,
        )
    except Exception:  # noqa: BLE001 - bu parça patladı, diğerleri devam etsin
        return {}
    if raw is None or raw.empty:
        return {}

    out: dict[str, pd.DataFrame] = {}
    if len(symbols) == 1:
        cleaned = _clean(raw)
        if resample:
            cleaned = _resample(cleaned, resample)
        return {symbols[0]: cleaned} if not cleaned.empty else {}

    for sym in symbols:
        try:
            sub = raw[sym]
        except Exception:  # noqa: BLE001 - o sembol dönmemiş olabilir
            continue
        cleaned = _clean(sub)
        if resample:
            cleaned = _resample(cleaned, resample)
        if not cleaned.empty:
            out[sym] = cleaned
    return out


@st.cache_data(ttl=_CACHE_TTL, show_spinner=False)
def get_many_daily(symbols: tuple[str, ...], period: str = "1y") -> dict[str, pd.DataFrame]:
    """Birden çok hisse için günlük OHLCV (büyük listelerde parça parça)."""
    if not symbols:
        return {}
    result: dict[str, pd.DataFrame] = {}
    for i in range(0, len(symbols), _CHUNK):
        result.update(_batch(list(symbols[i:i + _CHUNK]), "1d", period))
    return result


def _resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Bir OHLCV tablosunu daha üst zaman dilimine toplar (örn. 1h -> 4h)."""
    if df is None or df.empty:
        return pd.DataFrame()
    agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    have = {k: v for k, v in agg.items() if k in df.columns}
    return df.resample(rule).agg(have).dropna(how="any")


@st.cache_data(ttl=_CACHE_TTL, show_spinner=False)
def get_many(
    symbols: tuple[str, ...],
    interval: str = "1d",
    period: str = "2y",
    resample: str | None = None,
) -> dict[str, pd.DataFrame]:
    """Birden çok hisse için istenen zaman diliminde OHLCV (batched).

    interval: yfinance aralığı ("15m", "1h", "1d", "1wk", "1mo"…).
    resample: verilirse (örn. "4h") her sembol o kurala göre yeniden toplanır
    (yfinance 4 saatlik veri vermediği için 1 saatlikten türetilir).
    """
    if not symbols:
        return {}
    result: dict[str, pd.DataFrame] = {}
    for i in range(0, len(symbols), _CHUNK):
        result.update(_batch(list(symbols[i:i + _CHUNK]), interval, period, resample))
    return result


def last_price_and_change(df: pd.DataFrame) -> tuple[float | None, float | None]:
    """Son (gecikmeli) kapanış ve bir önceki kapanışa göre % değişim."""
    if df is None or df.empty or "Close" not in df or len(df) < 1:
        return None, None
    close = df["Close"].dropna()
    if close.empty:
        return None, None
    last = float(close.iloc[-1])
    if len(close) < 2:
        return last, None
    prev = float(close.iloc[-2])
    pct = (last / prev - 1.0) * 100.0 if prev else None
    return last, pct


def clear_cache() -> None:
    """Kullanıcı 'Yenile' derse önbelleği temizle."""
    get_history.clear()
    get_many_daily.clear()
    get_many.clear()
