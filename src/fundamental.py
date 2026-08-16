"""Temel (fundamental) tarama — borsapy / İş Yatırım verisiyle.

yfinance yalnızca fiyat/teknik veri verir. borsapy ise F/K, PD/DD, özsermaye
karlılığı (ROE), temettü verimi gibi TEMEL kriterlerle BIST'in tamamını
(İş Yatırım verisiyle) tarayabilir ve 797 şirketlik tam evreni sağlar.

Bu modül borsapy'yi TEMBEL (lazy) ve KORUMALI biçimde sarar: borsapy kurulu
değilse ya da hata verirse uygulama ÇÖKMEZ — sadece Temel Tarama sekmesi
"şu an kullanılamıyor" der, diğer sekmeler (yfinance) çalışmaya devam eder.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

# screen_stocks çıktısındaki İş Yatırım alan-id'lerini okunur adlara eşler.
# (id'ler tek tek filtre çalıştırılarak doğrulandı — bkz. README.)
COLUMN_NAMES: dict[str, str] = {
    "symbol": "Kod",
    "name": "Ad",
    "criteria_28": "F/K",
    "criteria_30": "PD/DD",
    "criteria_422": "ROE %",
    "criteria_33": "Temettü %",
    "criteria_8": "Piyasa Değeri (mn $)",
    "criteria_119": "Net Marj %",
    "criteria_61": "Getiri Pot. %",
}


@st.cache_data(ttl=3600, show_spinner=False)
def is_available() -> bool:
    """borsapy içe aktarılabiliyor mu?"""
    try:
        import borsapy  # noqa: F401
        return True
    except Exception:
        return False


@st.cache_data(ttl=3600, show_spinner=False)
def _criteria_map() -> dict:
    """screen_stocks çıktısındaki 'criteria_<id>' kolonlarını Türkçe ada eşler."""
    try:
        import borsapy as bp
        return {f"criteria_{it['id']}": it["name"] for it in bp.screener_criteria()}
    except Exception:
        return {}


@st.cache_data(ttl=86400, show_spinner=False)
def universe() -> dict:
    """Tüm BIST evreni: {'THYAO.IS': 'Ad', ...}. borsapy yoksa {} döner."""
    try:
        import borsapy as bp
        df = bp.companies()
        return {f"{t}.IS": str(n) for t, n in zip(df["ticker"], df["name"])}
    except Exception:
        return {}


@st.cache_data(ttl=1800, show_spinner=False)
def screen(
    index: str | None = None,
    pe_min: float | None = None,
    pe_max: float | None = None,
    pb_max: float | None = None,
    roe_min: float | None = None,
    dividend_yield_min: float | None = None,
    market_cap_min: float | None = None,
) -> pd.DataFrame:
    """borsapy.screen_stocks sarmalayıcısı; kolon adlarını Türkçeleştirir.

    Hata durumunda çağıran taraf (app.py) try/except ile yakalar.
    """
    import borsapy as bp

    kwargs = {
        k: v
        for k, v in dict(
            index=index,
            pe_min=pe_min,
            pe_max=pe_max,
            pb_max=pb_max,
            roe_min=roe_min,
            dividend_yield_min=dividend_yield_min,
            market_cap_min=market_cap_min,
        ).items()
        if v is not None
    }
    df = bp.screen_stocks(**kwargs)
    if df is None or df.empty:
        return pd.DataFrame()
    # Önce screener_criteria() defterini, üstüne doğrulanmış statik adları uygula.
    names = {**_criteria_map(), **COLUMN_NAMES}
    return df.rename(columns={c: names.get(c, c) for c in df.columns})
