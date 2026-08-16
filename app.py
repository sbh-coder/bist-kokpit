"""BIST Kokpit — izleme · grafik · tarama · backtest.

Karar-DESTEK aracı: veriyi gösterir, kullanıcının kendi tanımladığı teknik
kuralların sinyallerini hesaplar ve stratejileri geçmişte test eder.
Otomatik emir GÖNDERMEZ ve yatırım tavsiyesi VERMEZ. Kararı ve emri kullanıcı
kendi aracı kurumunda verir.

Çalıştırma:  streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src import auth, backtest, data, fundamental, indicators, scans, screener, symbols
from src.symbols import BIST_SYMBOLS, DEFAULT_WATCHLIST, label

st.set_page_config(page_title="BIST Kokpit", page_icon="📈", layout="wide")

# Mobil uyumu: telefonda kolonlar alt alta insin, kenar boşlukları daralsın,
# tablo/grafik ekrana sığsın. (Küçük ekran = <= 640px)
st.markdown(
    """
    <style>
    @media (max-width: 640px) {
      [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
      [data-testid="stHorizontalBlock"] > div { min-width: 100% !important; }
      .block-container { padding: 2.6rem 0.7rem 1rem !important; }
      h1 { font-size: 1.6rem !important; }
    }
    /* Tablo ve grafikler asla yatay taşmasın, kendi içinde kayabilsin */
    [data-testid="stDataFrame"], .stPlotlyChart { overflow-x: auto; }
    </style>
    """,
    unsafe_allow_html=True,
)

DISCLAIMER = (
    "⚠️ Bu araç yalnızca izleme, tarama ve geriye dönük test amaçlıdır. "
    "Gösterilen sinyaller, seçtiğiniz teknik kuralların mekanik sonucudur; "
    "**yatırım tavsiyesi değildir**. Veriler Yahoo Finance kaynaklıdır ve "
    "BIST için ~15 dakika gecikmelidir. İşlem kararını ve emri siz verirsiniz."
)

# --------------------------------------------------------------------------
# Giriş kapısı
# --------------------------------------------------------------------------
st.title("📈 BIST Kokpit")
if not auth.require_login():
    st.stop()

# borsapy varsa tüm BIST evrenini (797 hisse) izleme-listesi seçeneklerine ekle.
# Yoksa sessizce curated ~40 hisseyle devam eder.
_universe = fundamental.universe()
if _universe:
    symbols.register(_universe)

# --------------------------------------------------------------------------
# Kenar çubuğu — izleme listesi ve ayarlar
# --------------------------------------------------------------------------
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = list(DEFAULT_WATCHLIST)

with st.sidebar:
    st.header("İzleme Listesi")
    all_bist = st.checkbox(
        f"🌐 Tüm BIST'i izle ({len(symbols.ALL_NAMES)} hisse)",
        value=False,
        help="Tüm BIST hisselerini izleme listesine alır. İlk yükleme birkaç dakika "
        "sürebilir ve veri kaynağı (Yahoo) yoğunlukta geçici sınır koyabilir.",
    )
    known = list(symbols.ALL_NAMES.keys())
    # Listede olmayan ama kullanıcının eklediği kodlar da seçili kalabilsin
    options = sorted(set(known) | set(st.session_state["watchlist"]))
    picked = st.multiselect(
        "Hisseler",
        options=options,
        default=st.session_state["watchlist"],
        format_func=label,
        disabled=all_bist,
    )
    if all_bist:
        st.caption(f"🌐 {len(symbols.ALL_NAMES)} hisse izleniyor — ilk yükleme uzun sürebilir.")
    else:
        st.session_state["watchlist"] = picked

    custom = st.text_input("Kod ekle (örn. SOKM.IS)", value="").strip().upper()
    if custom:
        if not custom.endswith(".IS"):
            custom = custom + ".IS"
        if st.button(f"➕ {custom} ekle"):
            if custom not in st.session_state["watchlist"]:
                st.session_state["watchlist"].append(custom)
            st.rerun()

    st.divider()
    if st.button("🔄 Verileri yenile (önbelleği temizle)"):
        data.clear_cache()
        st.rerun()

    st.caption(DISCLAIMER)

if all_bist:
    watchlist = tuple(sorted(symbols.ALL_NAMES.keys()))
else:
    watchlist = tuple(st.session_state["watchlist"])

st.info(DISCLAIMER, icon="⚠️")

with st.expander("ℹ️ Nasıl kullanılır? (sekmelerin açıklaması)"):
    st.markdown(
        """
**👀 İzleme** — Takip listendeki hisselerin son (15 dk gecikmeli) fiyatı, günlük/haftalık
değişimi, RSI'ı ve "altın çapraz" durumu tek tabloda. Yeşil = artış, kırmızı = düşüş.

**📊 Grafik & Göstergeler** — Seçtiğin hissenin mum grafiği + hareketli ortalamalar
(SMA50/200, EMA20), RSI ve MACD panelleri. Zaman dilimini (günlük / 15 dakikalık /
saatlik / haftalık) değiştirebilirsin.

**🔎 Teknik Tarama** — Fiyat/gösterge kurallarıyla hisse tarar
(örn. "RSI 35'in altındakiler", "altın çaprazı olanlar").

**🧮 Temel Tarama** — Şirketlerin mali verileriyle tarar: F/K, PD/DD, özsermaye
karlılığı (ROE), temettü verimi — İş Yatırım verisi.

**🧪 Backtest** — Bir stratejinin (SMA kesişimi / RSI / MACD) geçmişte nasıl sonuç
verdiğini test eder; komisyon dahil, "al & tut" ile kıyaslar.

---
**Göstergeleri okuma (kısa):**
- **RSI (0–100):** 30 altı "aşırı satım", 70 üstü "aşırı alım" bölgesi sayılır.
- **Altın Çapraz:** 50 günlük ortalamanın 200 günlüğün üstüne çıkması (tersi "ölüm çaprazı").
- **MACD:** İki çizginin kesişimi momentum değişimi olarak okunur.

⚠️ Bunlar mekanik göstergelerdir, **yatırım tavsiyesi değildir**. Karar ve emir sana aittir.
        """
    )

tab_watch, tab_chart, tab_screen, tab_fund, tab_bt = st.tabs(
    [
        "👀 İzleme",
        "📊 Grafik & Göstergeler",
        "🔎 Teknik Tarama",
        "🧮 Temel Tarama",
        "🧪 Backtest",
    ]
)


# --------------------------------------------------------------------------
# Yardımcı: mum + gösterge grafiği
# --------------------------------------------------------------------------
def make_price_figure(df: pd.DataFrame, title: str) -> go.Figure:
    dfi = indicators.add_indicators(df)
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(title, "RSI (14)", "MACD"),
    )
    # Fiyat + hareketli ortalamalar
    fig.add_trace(
        go.Candlestick(
            x=dfi.index,
            open=dfi["Open"],
            high=dfi["High"],
            low=dfi["Low"],
            close=dfi["Close"],
            name="Fiyat",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1,
        col=1,
    )
    for col, color in (("SMA50", "#f9a825"), ("SMA200", "#6a1b9a"), ("EMA20", "#1e88e5")):
        if col in dfi:
            fig.add_trace(
                go.Scatter(x=dfi.index, y=dfi[col], name=col, line=dict(width=1, color=color)),
                row=1,
                col=1,
            )
    # RSI
    fig.add_trace(
        go.Scatter(x=dfi.index, y=dfi["RSI"], name="RSI", line=dict(color="#5e35b1")),
        row=2,
        col=1,
    )
    fig.add_hline(y=70, line=dict(color="#ef5350", dash="dash", width=1), row=2, col=1)
    fig.add_hline(y=30, line=dict(color="#26a69a", dash="dash", width=1), row=2, col=1)
    # MACD
    fig.add_trace(
        go.Bar(x=dfi.index, y=dfi["MACD_hist"], name="Histogram", marker_color="#90a4ae"),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=dfi.index, y=dfi["MACD"], name="MACD", line=dict(color="#1e88e5")),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=dfi.index, y=dfi["MACD_signal"], name="Sinyal", line=dict(color="#f9a825")),
        row=3,
        col=1,
    )
    fig.update_layout(
        height=720,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.02, yanchor="bottom"),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


# --------------------------------------------------------------------------
# TAB 1 — İzleme
# --------------------------------------------------------------------------
with tab_watch:
    if not watchlist:
        st.warning("Kenar çubuğundan en az bir hisse seçin.")
    else:
        with st.spinner("Veriler çekiliyor…"):
            wl_data = data.get_many_daily(watchlist, period="1y")
        table = screener.build_table(wl_data)
        if table.empty:
            st.error("Veri alınamadı. 'Verileri yenile'yi deneyin (Yahoo rate-limit olabilir).")
        else:
            show = table.drop(columns=["_symbol"], errors="ignore")

            def _style(v):
                if isinstance(v, (int, float)):
                    if v > 0:
                        return "color: #2e7d32"
                    if v < 0:
                        return "color: #c62828"
                return ""

            fmt = {
                "Fiyat": "{:.2f}",
                "Günlük %": "{:+.2f}",
                "Haftalık %": "{:+.2f}",
                "RSI(14)": "{:.1f}",
            }
            styled = show.style.format(fmt, na_rep="—").map(
                _style, subset=["Günlük %", "Haftalık %"]
            )
            st.dataframe(styled, use_container_width=True, hide_index=True)
            st.caption(
                "Altın Çapraz = 50 günlük ortalama 200 günlüğün üstünde. "
                "RSI < 30 aşırı satım, > 70 aşırı alım bölgesi olarak yorumlanır."
            )


# --------------------------------------------------------------------------
# TAB 2 — Grafik & Göstergeler
# --------------------------------------------------------------------------
with tab_chart:
    if not watchlist:
        st.warning("Kenar çubuğundan en az bir hisse seçin.")
    else:
        c1, c2 = st.columns([2, 1])
        with c1:
            sym = st.selectbox("Hisse", options=list(watchlist), format_func=label)
        with c2:
            interval_label = st.selectbox(
                "Zaman dilimi",
                options=[
                    "Günlük (1d)",
                    "15 dakikalık (~15 dk gecikmeli)",
                    "Saatlik (1h)",
                    "Haftalık (1wk)",
                    "Aylık (1mo)",
                ],
            )
        interval_map = {
            "Günlük (1d)": ("1d", "2y"),
            "15 dakikalık (~15 dk gecikmeli)": ("15m", "60d"),
            "Saatlik (1h)": ("1h", "180d"),
            "Haftalık (1wk)": ("1wk", "5y"),
            "Aylık (1mo)": ("1mo", "max"),
        }
        interval, period = interval_map[interval_label]

        with st.spinner("Grafik hazırlanıyor…"):
            df = data.get_history(sym, period=period, interval=interval)
        if df.empty:
            st.error("Bu hisse/zaman dilimi için veri gelmedi.")
        else:
            last, pct = data.last_price_and_change(df)
            m1, m2 = st.columns(2)
            m1.metric("Son (gecikmeli) fiyat", f"{last:,.2f} ₺" if last else "—")
            m2.metric("Değişim", f"{pct:+.2f} %" if pct is not None else "—")
            st.plotly_chart(make_price_figure(df, label(sym)), use_container_width=True)


# --------------------------------------------------------------------------
# TAB 3 — Teknik Tarama (yfinance verisi)
# --------------------------------------------------------------------------
with tab_screen:
    st.subheader("Teknik Tarama")
    st.caption(
        f"En sık kullanılan {len(scans.SCANS)} hazır teknik tarama (yfinance verisi). "
        "Sonuçlar mekanik kurallardır, yatırım tavsiyesi değildir. Temel kriterler "
        "(F/K, ROE…) için '🧮 Temel Tarama' sekmesini kullanın."
    )
    tk_uni_choice = st.radio(
        "Evren",
        options=["İzleme listem", f"Öne çıkan liste ({len(BIST_SYMBOLS)} hisse)"],
        horizontal=True,
        key="tk_uni",
    )
    tk_universe = (
        watchlist if tk_uni_choice == "İzleme listem" else tuple(BIST_SYMBOLS.keys())
    )

    # Zaman dilimi -> (yfinance aralığı, veri süresi, yeniden-toplama kuralı)
    TF = {
        "15 dakika": ("15m", "60d", None),
        "1 saat": ("1h", "730d", None),
        "4 saat": ("1h", "730d", "4h"),
        "1 gün": ("1d", "2y", None),
        "1 hafta": ("1wk", "10y", None),
        "1 ay": ("1mo", "max", None),
    }
    tk_tf = st.selectbox("Zaman dilimi", options=list(TF.keys()), index=3, key="tk_tf")
    tk_interval, tk_period, tk_resample = TF[tk_tf]
    if tk_interval in ("15m", "1h"):
        st.caption(
            "⏱️ Kısa zaman dilimlerinde çok hisse taramak biraz uzun sürebilir; "
            "veriler ~15 dk gecikmelidir. ('gün/hafta' ifadeleri seçilen zaman "
            "dilimindeki bar sayısı olarak hesaplanır.)"
        )

    tk_mode = st.radio(
        "Tarama türü", ["Hazır taramalar", "Özel kural"], horizontal=True, key="tk_mode"
    )

    if len(tk_universe) > 200 and tk_interval in ("15m", "1h"):
        st.warning(
            "⚠️ Çok sayıda hisseyi kısa zaman diliminde (15dk/1s) taramak uzun "
            "sürebilir veya veri sınırına takılabilir. Günlük/haftalık önerilir."
        )

    if tk_mode == "Hazır taramalar":
        run_all = st.checkbox(
            "🔬 Tüm taramaları birlikte çalıştır (hisse bazında ✓ matris)",
            value=False,
            key="tk_all",
        )
        if run_all:
            selected_scans = list(scans.SCANS.keys())
            st.caption(
                f"ℹ️ {len(selected_scans)} taramanın tamamı çalışacak; sonuç hisse "
                "bazında, en çok eşleşen üstte olacak şekilde matris olarak gösterilir."
            )
        else:
            selected_scans = st.multiselect(
                "Tarama(lar) seç — bir veya birden fazla",
                options=list(scans.SCANS.keys()),
                default=[next(iter(scans.SCANS.keys()))],
                key="tk_scans",
            )
            if len(selected_scans) == 1:
                st.caption("ℹ️ " + scans.SCANS[selected_scans[0]][0])

        if st.button("🔎 Tara", type="primary", key="tk_run_preset"):
            if not tk_universe:
                st.warning("Taranacak hisse yok.")
            elif not selected_scans:
                st.warning("En az bir tarama seçin.")
            else:
                with st.spinner("Taranıyor…"):
                    d = data.get_many(
                        tuple(tk_universe), tk_interval, tk_period, tk_resample
                    )
                    if len(selected_scans) == 1:
                        res = scans.run_scan(selected_scans[0], d)
                    else:
                        res = scans.run_scans(selected_scans, d)
                st.write(f"**{len(res)}** hisse eşleşti (taranan: {len(d)}).")
                if not res.empty:
                    st.dataframe(res, use_container_width=True, hide_index=True)
                else:
                    st.info("Eşleşen hisse bulunamadı.")
    else:
        st.markdown("**Kendi kuralını kur:**")
        f1, f2, f3 = st.columns(3)
        with f1:
            use_rsi = st.checkbox("RSI üst sınırı", value=True)
            rsi_max = st.slider("RSI ≤", 5, 95, 35, disabled=not use_rsi)
        with f2:
            only_golden = st.checkbox("Sadece Altın Çapraz (50>200)", value=False)
            only_above50 = st.checkbox("Fiyat 50 günlük üstünde", value=False)
        with f3:
            use_daymove = st.checkbox("Min. günlük %", value=False)
            min_day = st.slider("Günlük % ≥", -10.0, 10.0, 0.0, 0.5, disabled=not use_daymove)

        if st.button("🔎 Tara", type="primary", key="tk_run_custom"):
            if not tk_universe:
                st.warning("Taranacak hisse yok.")
            else:
                with st.spinner("Taranıyor…"):
                    scan_data = data.get_many(
                        tuple(tk_universe), tk_interval, tk_period, tk_resample
                    )
                    base = screener.build_table(scan_data)
                    res = screener.apply_filters(
                        base,
                        rsi_max=rsi_max if use_rsi else None,
                        only_golden_cross=only_golden,
                        only_above_sma50=only_above50,
                        min_day_pct=min_day if use_daymove else None,
                    )
                st.write(f"**{len(res)}** hisse kurala uydu (taranan: {len(base)}).")
                if not res.empty:
                    st.dataframe(
                        res.drop(columns=["_symbol"], errors="ignore"),
                        use_container_width=True,
                        hide_index=True,
                    )


# --------------------------------------------------------------------------
# TAB 4 — Temel Tarama (borsapy / İş Yatırım verisi)
# --------------------------------------------------------------------------
with tab_fund:
    st.subheader("Temel (fundamental) tarama — İş Yatırım verisi")
    if not fundamental.is_available():
        st.warning(
            "Temel tarama için `borsapy` kütüphanesi gerekli ama şu an "
            "kullanılamıyor. `pip install borsapy` ile eklenebilir. "
            "Diğer sekmeler etkilenmez."
        )
    else:
        st.caption(
            "F/K, PD/DD, özsermaye karlılığı (ROE), temettü verimi gibi TEMEL "
            "kriterlerle tüm BIST'i tarar (İş Yatırım verisi). Sonuçlar bilgi "
            "amaçlıdır, yatırım tavsiyesi değildir."
        )
        g1, g2, g3 = st.columns(3)
        with g1:
            index_sel = st.selectbox("Endeks", ["Tüm BIST", "XU030", "XU050", "XU100"])
            pe_max = st.number_input("F/K en fazla (0 = kapalı)", min_value=0.0, value=15.0, step=1.0)
        with g2:
            pb_max = st.number_input("PD/DD en fazla (0 = kapalı)", min_value=0.0, value=0.0, step=0.5)
            roe_min = st.number_input("ROE % en az (0 = kapalı)", min_value=0.0, value=0.0, step=5.0)
        with g3:
            dy_min = st.number_input("Temettü verimi % en az (0 = kapalı)", min_value=0.0, value=0.0, step=1.0)
            mcap_min = st.number_input("Piyasa değeri (mn $) en az (0 = kapalı)", min_value=0.0, value=0.0, step=100.0)

        if st.button("🧮 Temel tara", type="primary"):
            idx = None if index_sel == "Tüm BIST" else index_sel
            try:
                with st.spinner("İş Yatırım verisiyle taranıyor…"):
                    res = fundamental.screen(
                        index=idx,
                        pe_min=0.0 if pe_max > 0 else None,
                        pe_max=pe_max if pe_max > 0 else None,
                        pb_max=pb_max if pb_max > 0 else None,
                        roe_min=roe_min if roe_min > 0 else None,
                        dividend_yield_min=dy_min if dy_min > 0 else None,
                        market_cap_min=mcap_min if mcap_min > 0 else None,
                    )
                if res.empty:
                    st.info("Kriterlere uyan hisse bulunamadı ya da veri gelmedi.")
                else:
                    st.write(f"**{len(res)}** hisse kriterlere uydu.")
                    st.dataframe(res, use_container_width=True, hide_index=True)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Temel tarama başarısız oldu: {exc}")


# --------------------------------------------------------------------------
# TAB 5 — Backtest
# --------------------------------------------------------------------------
with tab_bt:
    st.subheader("Stratejiyi geçmişte test et")
    st.caption(
        "Sonuçlar varsayımsaldır ve komisyon dışında gerçek sürtünmeleri "
        "(kayma, likidite, fiyat adımı) tam yansıtmaz. Yatırım tavsiyesi değildir."
    )
    if not watchlist:
        st.warning("Kenar çubuğundan en az bir hisse seçin.")
    else:
        b1, b2, b3 = st.columns(3)
        with b1:
            bt_sym = st.selectbox("Hisse", options=list(watchlist), format_func=label, key="bt_sym")
        with b2:
            strat_name = st.selectbox("Strateji", options=list(backtest.STRATEGIES.keys()))
        with b3:
            years = st.slider("Kaç yıllık veri", 1, 5, 3)

        commission = st.slider("Komisyon (tek yön, %)", 0.0, 0.5, 0.15, 0.05) / 100.0

        # Stratejiye özel parametreler
        params: dict = {}
        if strat_name == "SMA Kesişimi (Altın/Ölüm Çaprazı)":
            p1, p2 = st.columns(2)
            params["fast"] = p1.number_input("Hızlı ortalama", 5, 100, 50)
            params["slow"] = p2.number_input("Yavaş ortalama", 20, 300, 200)
        elif strat_name == "RSI Ortalamaya Dönüş (30/70)":
            p1, p2 = st.columns(2)
            params["buy_below"] = p1.number_input("Al: RSI <", 5, 50, 30)
            params["sell_above"] = p2.number_input("Sat: RSI >", 50, 95, 70)

        if st.button("🧪 Backtest çalıştır", type="primary"):
            with st.spinner("Hesaplanıyor…"):
                df = data.get_history(bt_sym, period=f"{years}y", interval="1d")
                if df.empty or len(df) < 60:
                    st.error("Yeterli veri yok.")
                else:
                    pos = backtest.STRATEGIES[strat_name](df, **params)
                    res = backtest.run(df, pos, commission=commission)

            if not df.empty and len(df) >= 60:
                m = res.metrics
                cols = st.columns(5)
                cols[0].metric("Strateji getiri", f"{m['Toplam getiri %']} %")
                cols[1].metric("Al-Tut getiri", f"{m['Al-Tut getiri %']} %")
                cols[2].metric("Maks. düşüş", f"{m['Maks. düşüş %']} %")
                cols[3].metric("Sharpe", m["Sharpe"])
                cols[4].metric(
                    "İşlem / Kazanan",
                    f"{m['İşlem sayısı']} / "
                    + (f"{m['Kazanan işlem %']}%" if m["Kazanan işlem %"] is not None else "—"),
                )

                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(x=res.equity.index, y=res.equity, name="Strateji", line=dict(color="#1e88e5"))
                )
                fig.add_trace(
                    go.Scatter(
                        x=res.buy_hold.index,
                        y=res.buy_hold,
                        name="Al & Tut",
                        line=dict(color="#90a4ae", dash="dash"),
                    )
                )
                fig.update_layout(
                    title="Sermaye eğrisi (100.000 ₺ başlangıç)",
                    height=420,
                    legend=dict(orientation="h", y=1.02, yanchor="bottom"),
                    margin=dict(l=10, r=10, t=40, b=10),
                )
                st.plotly_chart(fig, use_container_width=True)

                if not res.trades.empty:
                    with st.expander(f"İşlem listesi ({len(res.trades)} işlem)"):
                        st.dataframe(res.trades, use_container_width=True, hide_index=True)
