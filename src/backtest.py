"""Şeffaf, vektörel geriye dönük test (backtest) motoru.

Amaç: kullanıcının KENDİ kuralını geçmiş veride sınamak. Kutu içinde
sihir yok — strateji fonksiyonu 0/1 (pozisyonda/dışında) bir seri üretir,
motor bunu bir sonraki bara uygulayarak (ileriye bakmayı önlemek için)
getiriyi, sermaye eğrisini ve metrikleri hesaplar.

Komisyon dahil edilir. Sonuçlar VARSAYIMSALDIR ve yatırım tavsiyesi değildir:
gerçek işlemde kayma (slippage), likidite, fiyat adımı ve devre kesici gibi
sürtünmeler bu basit modelde tam yansımaz.

İleride daha gelişmiş emir modeli için `backtesting.py` kütüphanesine
geçilebilir (README); bu motor eğitim ve şeffaflık için bilinçli olarak sadedir.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import indicators as ind

TRADING_DAYS = 252


# --------------------------------------------------------------------------
# Stratejiler: her biri df -> pozisyon serisi (1 = pozisyonda, 0 = nakit)
# --------------------------------------------------------------------------
def strat_sma_crossover(df: pd.DataFrame, fast: int = 50, slow: int = 200) -> pd.Series:
    """Hızlı ortalama yavaşın üstündeyse pozisyonda kal (trend takibi)."""
    close = df["Close"]
    f = ind.sma(close, fast)
    s = ind.sma(close, slow)
    pos = (f > s).astype(float)
    pos[f.isna() | s.isna()] = 0.0
    return pos


def strat_rsi_reversion(
    df: pd.DataFrame, buy_below: float = 30.0, sell_above: float = 70.0, period: int = 14
) -> pd.Series:
    """RSI aşırı satımda al, aşırı alımda çık (ortalamaya dönüş)."""
    r = ind.rsi(df["Close"], period)
    raw = pd.Series(np.nan, index=df.index)
    raw[r < buy_below] = 1.0
    raw[r > sell_above] = 0.0
    return raw.ffill().fillna(0.0)


def strat_macd_crossover(df: pd.DataFrame) -> pd.Series:
    """MACD çizgisi sinyal çizgisinin üstündeyse pozisyonda kal."""
    m = ind.macd(df["Close"])
    pos = (m["macd"] > m["signal"]).astype(float)
    pos[m["macd"].isna() | m["signal"].isna()] = 0.0
    return pos


STRATEGIES = {
    "SMA Kesişimi (Altın/Ölüm Çaprazı)": strat_sma_crossover,
    "RSI Ortalamaya Dönüş (30/70)": strat_rsi_reversion,
    "MACD Kesişimi": strat_macd_crossover,
}


# --------------------------------------------------------------------------
# Motor
# --------------------------------------------------------------------------
@dataclass
class BacktestResult:
    equity: pd.Series
    buy_hold: pd.Series
    metrics: dict
    trades: pd.DataFrame = field(default_factory=pd.DataFrame)


def run(
    df: pd.DataFrame,
    position: pd.Series,
    *,
    commission: float = 0.0015,  # tek yönde %0.15 (ayarlanabilir)
    initial: float = 100_000.0,
) -> BacktestResult:
    """Pozisyon serisini geçmiş fiyata uygulayıp sonuç üretir."""
    close = df["Close"].astype(float)
    ret = close.pct_change().fillna(0.0)

    # Kararı bir sonraki barda uygula -> ileriye bakma (look-ahead) yok
    acting = position.shift(1).fillna(0.0).clip(0, 1)

    # İşlem maliyeti: pozisyon her değiştiğinde komisyon
    turnover = acting.diff().abs().fillna(acting.abs())
    cost = turnover * commission

    strat_ret = acting * ret - cost
    equity = (1.0 + strat_ret).cumprod() * initial
    buy_hold = (1.0 + ret).cumprod() * initial

    metrics = _metrics(strat_ret, equity, buy_hold, initial)
    trades = _extract_trades(close, acting, commission)
    if not trades.empty:
        wins = (trades["Getiri %"] > 0).sum()
        metrics["İşlem sayısı"] = int(len(trades))
        metrics["Kazanan işlem %"] = round(100.0 * wins / len(trades), 1)
    else:
        metrics["İşlem sayısı"] = 0
        metrics["Kazanan işlem %"] = None

    return BacktestResult(equity=equity, buy_hold=buy_hold, metrics=metrics, trades=trades)


def _metrics(strat_ret: pd.Series, equity: pd.Series, buy_hold: pd.Series, initial: float) -> dict:
    n = len(strat_ret)
    years = n / TRADING_DAYS if n else 0.0
    total = equity.iloc[-1] / initial - 1.0 if n else 0.0
    bh_total = buy_hold.iloc[-1] / initial - 1.0 if n else 0.0
    cagr = (equity.iloc[-1] / initial) ** (1 / years) - 1.0 if years > 0 else 0.0

    std = strat_ret.std()
    sharpe = (strat_ret.mean() / std) * np.sqrt(TRADING_DAYS) if std and std > 0 else 0.0

    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    max_dd = drawdown.min() if n else 0.0

    return {
        "Toplam getiri %": round(total * 100, 1),
        "Al-Tut getiri %": round(bh_total * 100, 1),
        "Yıllık (CAGR) %": round(cagr * 100, 1),
        "Maks. düşüş %": round(max_dd * 100, 1),
        "Sharpe": round(sharpe, 2),
    }


def _extract_trades(close: pd.Series, acting: pd.Series, commission: float) -> pd.DataFrame:
    """Pozisyon 0->1 (giriş) ve 1->0 (çıkış) geçişlerinden işlem listesi çıkarır."""
    rows = []
    in_pos = False
    entry_price = 0.0
    entry_date = None
    prices = close.values
    positions = acting.values
    idx = close.index

    for i in range(len(positions)):
        if not in_pos and positions[i] == 1:
            in_pos = True
            entry_price = prices[i]
            entry_date = idx[i]
        elif in_pos and positions[i] == 0:
            in_pos = False
            r = prices[i] / entry_price - 1.0 - 2 * commission
            rows.append((entry_date, idx[i], round(r * 100, 2)))

    if in_pos and entry_price:  # açık pozisyon: son fiyata göre kapat
        r = prices[-1] / entry_price - 1.0 - commission
        rows.append((entry_date, idx[-1], round(r * 100, 2)))

    return pd.DataFrame(rows, columns=["Giriş", "Çıkış", "Getiri %"])
