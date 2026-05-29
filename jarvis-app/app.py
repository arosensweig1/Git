"""JARVIS — ECM Prospecting Terminal (Streamlit).

Gateway:  website login  ->  connect data sources  ->  Enter Jarvis.
The 'Verify connection & pulls' page is what you run first with your real
credentials to confirm everything authenticates and is pulling.

Run locally:   streamlit run app.py        (opens http://localhost:8501)

This app NEVER sends email. It drafts and queues for human review only.
"""
import os
import tempfile
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import auth
import connections as conn
from data_market import CapIQProvider, CAPIQ_FIELD_MAP
from data_crm import load_crm_rows
from pipeline import build_target_list

load_dotenv()
st.set_page_config(page_title="JARVIS · ECM Terminal", page_icon="🛰️", layout="wide")

MONTHS = int(os.getenv("MONTHS_THRESHOLD", "24"))
CAP = int(os.getenv("MARKET_CAP_CAP", "500000000"))


def _capiq():
    c = st.session_state.get("capiq_creds", {})
    return CapIQProvider(c.get("base"), c.get("user"), c.get("pwd"), c.get("key"))


def _excel_path():
    up = st.session_state.get("dc_excel")
    if up is None:
        return None
    tmp = os.path.join(tempfile.gettempdir(), "Deal_CLoud.xlsx")
    with open(tmp, "wb") as f:
        f.write(up.getbuffer())
    return tmp


# ----------------------------------------------------------------------------
# Gateway
# ----------------------------------------------------------------------------
if not auth.login_gate():
    st.stop()

auth.logout_button()
st.sidebar.title("JARVIS")
MONTHS = st.sidebar.number_input("Months threshold", 1, 120, MONTHS)
CAP = st.sidebar.number_input("Market-cap cap ($)", 1_000_000, 5_000_000_000, CAP, step=50_000_000)

page = st.sidebar.radio("Page", ["Connect", "Verify connection & pulls", "Blotter"])

# ----------------------------------------------------------------------------
if page == "Connect":
    conn.connect_screen()
    st.divider()
    if conn.can_enter():
        st.success("Cap IQ connected and a CRM source is available — go to "
                   "'Verify connection & pulls' or 'Blotter'.")
    else:
        st.info("Connect Cap IQ and provide a CRM source (DealCloud or an uploaded "
                "Deal_CLoud.xlsx) to proceed.")

# ----------------------------------------------------------------------------
elif page == "Verify connection & pulls":
    st.subheader("Verify connection & pulls")
    st.caption("Confirms your credentials authenticate and reports which mapped Cap IQ "
               "fields are entitled. Fill CAPIQ_FIELD_MAP in data_market.py with your "
               "real mnemonics first.")

    probe = st.text_input("Cap IQ probe identifier", "IBM:")
    if st.button("Run Cap IQ connection test", type="primary"):
        prov = _capiq()
        if not prov.configured():
            st.error("Cap IQ not configured — set credentials on the Connect page.")
        else:
            res = prov.connection_test(probe)
            a = res.pop("_auth")
            (st.success if a["ok"] else st.error)(a["detail"])
            if a["ok"]:
                df = pd.DataFrame([
                    {"field": k, "mnemonic": v.get("mnemonic", ""),
                     "status": v.get("status", ""), "sample": v.get("sample", "")}
                    for k, v in res.items()
                ])
                st.dataframe(df, use_container_width=True, hide_index=True)
                entitled = sum(1 for v in res.values() if v.get("status") == "ok")
                st.metric("Entitled fields", f"{entitled} / {len(res)}")

    st.divider()
    st.markdown("**CRM source test**")
    if st.button("Test CRM (DealCloud or Excel)"):
        rows, src, banner = load_crm_rows(_excel_path())
        if banner:
            st.warning(banner)
        st.write(f"Source: **{src}** — {len(rows)} rows")
        if rows:
            st.dataframe(pd.DataFrame(rows).head(20), use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("**EDGAR filings test** (public — no credentials needed)")
    etk = st.text_input("Ticker for EDGAR lookup", "AAPL")
    if st.button("Test EDGAR (financing docs)"):
        import edgar
        try:
            docs = edgar.financing_docs(etk)
            recent = edgar.recent_filings(etk, limit=8)
            for label, d in (("Latest prospectus", docs["prospectus"]),
                             ("Latest 8-K/6-K", docs["transaction"])):
                if d:
                    st.markdown(f"- **{label}** ({d['form']}, {d['date']}): [{d['url']}]({d['url']})")
                else:
                    st.markdown(f"- {label}: none found")
            if recent:
                st.dataframe(pd.DataFrame(recent)[["form", "date", "url"]],
                             use_container_width=True, hide_index=True)
        except Exception as e:  # noqa: BLE001
            st.error(f"EDGAR lookup failed: {e}")

# ----------------------------------------------------------------------------
elif page == "Blotter":
    st.subheader("Blotter")
    if not conn.can_enter():
        st.info("Connect Cap IQ + a CRM source first.")
        st.stop()
    with st.spinner("Building target list…"):
        crm_rows, src, banner = load_crm_rows(_excel_path())
        if banner:
            st.warning(banner)
        try:
            universe = _capiq().get_universe()
        except Exception as e:  # noqa: BLE001
            universe = []
            st.warning(f"Set B universe unavailable: {e} "
                       "(confirm CAPIQ_UNIVERSE_SCREEN_ID + list-expansion call).")
        targets = build_target_list(crm_rows, universe, MONTHS, CAP)
    a = sum(1 for t in targets if t["source_set"] == "A")
    b = sum(1 for t in targets if t["source_set"] == "B")
    both = sum(1 for t in targets if t["source_set"] == "both")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Set A (CRM revival)", a + both)
    c2.metric("Set B (small-cap)", b + both)
    c3.metric("Both", both)
    c4.metric("Final", len(targets))
    if targets:
        st.dataframe(pd.DataFrame(targets)[["company", "ticker", "exchange",
                     "source_set", "reason"]], use_container_width=True, hide_index=True)
    else:
        st.info("No targets yet — add Cap IQ universe expansion and/or CRM rows.")
    st.caption("Demo of pipeline wiring. Per-company Cap IQ dashboard + email drafting "
               "are the next build step once the field map is confirmed.")
