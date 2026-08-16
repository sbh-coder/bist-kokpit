"""Basit şifre kapısı.

Tarayıcıda herkese açık bir URL'de yayınlanacağı için, uygulamayı basit
bir parola arkasına alır. Parola `.streamlit/secrets.toml` içindeki
`app_password` değerinden okunur.

Eğer parola tanımlı DEĞİLSE (örn. lokal geliştirme), kapı açık geçer ama
uyarı gösterir. Yayına almadan önce mutlaka bir parola tanımlayın.

Not: Bu, banka seviyesi güvenlik değil, "linki bilen herkes girmesin"
seviyesinde bir korumadır. Uygulama zaten yalnızca piyasa verisi ve
kullanıcının kendi stratejilerini içerir; para/parola/işlem yoktur.
"""
from __future__ import annotations

import hmac

import streamlit as st


def _password_configured() -> bool:
    try:
        return bool(st.secrets.get("app_password", ""))
    except Exception:  # noqa: BLE001 - secrets dosyası hiç yoksa
        return False


def require_login() -> bool:
    """Giriş yapıldıysa True döner; aksi halde form gösterir ve False döner."""
    if not _password_configured():
        st.info(
            "🔓 Parola tanımlı değil (geliştirme modu). Yayına almadan önce "
            "`.streamlit/secrets.toml` içine `app_password` ekleyin."
        )
        return True

    if st.session_state.get("_authenticated"):
        return True

    def _check() -> None:
        entered = st.session_state.get("_pw", "")
        if hmac.compare_digest(entered, str(st.secrets["app_password"])):
            st.session_state["_authenticated"] = True
            st.session_state.pop("_pw", None)
        else:
            st.session_state["_authenticated"] = False

    st.text_input("🔑 Parola", type="password", key="_pw", on_change=_check)
    if st.session_state.get("_authenticated") is False:
        st.error("Parola hatalı.")
    return False
