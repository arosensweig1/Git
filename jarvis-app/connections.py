"""Connect screen: collect API credentials (prefilled from .env), test each
vendor, and hold them in session. 'Remember on this server' can persist to .env."""
import os
import streamlit as st
from dotenv import load_dotenv, set_key, find_dotenv

from data_market import CapIQProvider
from data_crm import DealCloudClient

load_dotenv()
_ENV_PATH = find_dotenv() or ".env"


def _persist(pairs):
    for k, v in pairs.items():
        if v:
            set_key(_ENV_PATH, k, v)


def connect_screen():
    st.subheader("Connect your data sources")
    st.caption("These are **API credentials**, provisioned by your firm admin / S&P rep — "
               "not the Cap IQ / DealCloud web-portal logins (separate SSO systems).")
    remember = st.checkbox("Remember on this server (writes to .env)", value=False)

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**Capital IQ** · sole market-data source")
        st.caption("[Portal (reference only)](https://www.capitaliq.spglobal.com/web/login)")
        base = st.text_input("Base URL", os.getenv("CAPIQ_BASE_URL", ""))
        user = st.text_input("API Username", os.getenv("CAPIQ_USERNAME", ""))
        pwd = st.text_input("API Password", os.getenv("CAPIQ_PASSWORD", ""), type="password")
        key = st.text_input("API Key (optional)", os.getenv("CAPIQ_API_KEY", ""), type="password")
        if st.button("Connect Cap IQ"):
            prov = CapIQProvider(base, user, pwd, key)
            ok, msg = prov.authenticate_test()
            st.session_state["capiq_ok"] = ok
            st.session_state["capiq_creds"] = dict(base=base, user=user, pwd=pwd, key=key)
            (st.success if ok else st.error)(msg)
            if remember and ok:
                _persist({"CAPIQ_BASE_URL": base, "CAPIQ_USERNAME": user,
                          "CAPIQ_PASSWORD": pwd, "CAPIQ_API_KEY": key})
        _status("capiq_ok")

    with c2:
        st.markdown("**DealCloud** · CRM coverage (or upload Excel)")
        st.caption("[Portal (reference only)](https://app.dealcloud.com/Account/login)")
        site = st.text_input("Site URL", os.getenv("DC_SITE_URL", ""))
        cid = st.text_input("Client ID", os.getenv("DC_CLIENT_ID", ""))
        csec = st.text_input("Client Secret", os.getenv("DC_CLIENT_SECRET", ""), type="password")
        if st.button("Connect DealCloud"):
            dc = DealCloudClient(site, cid, csec)
            ok, msg = dc.test_connection()
            st.session_state["dc_ok"] = ok
            (st.success if ok else st.error)(msg)
            if remember and ok:
                _persist({"DC_SITE_URL": site, "DC_CLIENT_ID": cid, "DC_CLIENT_SECRET": csec})
        _status("dc_ok")
        st.file_uploader("…or upload Deal_CLoud.xlsx (CRM fallback)", type=["xlsx"],
                         key="dc_excel")


def _status(flag):
    v = st.session_state.get(flag)
    if v is True:
        st.markdown("🟢 connected")
    elif v is False:
        st.markdown("🔴 failed")
    else:
        st.markdown("🟠 not configured")


def crm_available():
    return st.session_state.get("dc_ok") is True or st.session_state.get("dc_excel") is not None


def can_enter():
    return st.session_state.get("capiq_ok") is True and crm_available()
