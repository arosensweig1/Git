"""CRM coverage. DealCloud via OAuth2 client-credentials, with the PART 7
Excel parser as the exact fallback. Field/object names differ per DealCloud
site, so they are exposed as config constants."""
import os
import time
import requests
import pandas as pd
from datetime import datetime

# ---- DealCloud per-site field/object mapping (edit to match your site) -------
DC_COMPANY_OBJECT = os.getenv("DC_COMPANY_OBJECT", "Company")
DC_LAST_OUTREACH_FIELD = os.getenv("DC_LAST_OUTREACH_FIELD", "LastOutreach")
DC_BANKER_FIELD = os.getenv("DC_BANKER_FIELD", "CoveringBanker")


# ============================================================================
# Excel fallback  (PART 7 reference parser — used verbatim)
# ============================================================================
def _clean(s):
    if s is None:
        return None
    s = str(s).replace("\xa0", " ").replace(" ", " ").strip()
    return s or None


def parse_outreach_date(raw):
    s = _clean(raw)
    if not s:
        return None
    for fmt in ("%m/%d/%Y %I:%M %p", "%m/%d/%Y %H:%M", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def read_dealcloud_excel(path, sheet_name="Sheet1"):
    # Header is on spreadsheet row 3 => header=2 (0-indexed). Column A is blank.
    df = pd.read_excel(path, sheet_name=sheet_name, header=2, engine="openpyxl")
    df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]
    df = df.rename(columns={c: str(c).strip() for c in df.columns})

    def col(*cands):
        for cand in cands:
            for c in df.columns:
                if str(c).strip().lower() == cand.lower():
                    return c
        return None

    c_name = col("Company Name")
    c_exch = col("Exchange")
    c_tick = col("Ticker Symbol", "Ticker")
    c_bank = col("Banker")
    c_date = col("Date of Outreach")

    rows = []
    for _, r in df.iterrows():
        company = _clean(r.get(c_name)) if c_name else None
        ticker  = _clean(r.get(c_tick)) if c_tick else None
        date    = parse_outreach_date(r.get(c_date)) if c_date else None
        if date is None:
            continue                      # need a date to apply the 24-month rule
        if not company and not ticker:
            continue                      # need something to identify the company
        rows.append({
            "company": company,
            "exchange": _clean(r.get(c_exch)) if c_exch else None,
            "ticker": ticker,
            "banker": _clean(r.get(c_bank)) if c_bank else None,
            "date_of_outreach": date,
        })
    return rows


# ============================================================================
# DealCloud API client (OAuth2 client-credentials)
# ============================================================================
class DealCloudClient:
    def __init__(self, site_url=None, client_id=None, client_secret=None):
        self.site_url = (site_url or os.getenv("DC_SITE_URL", "")).rstrip("/")
        self.client_id = client_id or os.getenv("DC_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("DC_CLIENT_SECRET", "")
        self._token = None
        self._token_exp = 0

    def configured(self):
        return bool(self.site_url and self.client_id and self.client_secret)

    def _auth(self):
        """POST {site}/api/rest/v1/oauth/token  grant_type=client_credentials."""
        url = f"{self.site_url}/api/rest/v1/oauth/token"
        resp = requests.post(
            url,
            data={"grant_type": "client_credentials", "scope": "data"},
            auth=(self.client_id, self.client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        resp.raise_for_status()
        tok = resp.json()
        self._token = tok["access_token"]
        # tokens expire ~900s; refresh a little early
        self._token_exp = time.time() + int(tok.get("expires_in", 900)) - 30
        return self._token

    def token(self):
        if not self._token or time.time() >= self._token_exp:
            return self._auth()
        return self._token

    def test_connection(self):
        try:
            self._auth()
            return True, "Authenticated (client-credentials token acquired)."
        except Exception as e:  # noqa: BLE001
            return False, f"DealCloud auth failed: {e}"

    def fetch_coverage(self):
        """Read company name, ticker, exchange, covering banker, last-outreach date.
        Object/field names are site-specific (see DC_* constants above)."""
        headers = {"Authorization": f"Bearer {self.token()}"}
        url = f"{self.site_url}/api/rest/v1/data/entry/{DC_COMPANY_OBJECT}"
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
        rows = []
        for rec in resp.json():
            rows.append({
                "company": rec.get("CompanyName") or rec.get("Name"),
                "ticker": rec.get("Ticker") or rec.get("TickerSymbol"),
                "exchange": rec.get("Exchange"),
                "banker": rec.get(DC_BANKER_FIELD),
                "date_of_outreach": _coerce_dt(rec.get(DC_LAST_OUTREACH_FIELD)),
            })
        return rows


def _coerce_dt(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    return parse_outreach_date(v)


def load_crm_rows(uploaded_excel_path=None):
    """DealCloud if configured & reachable, else the uploaded Excel fallback.
    Returns (rows, source_label, banner_or_None)."""
    dc = DealCloudClient()
    if dc.configured():
        try:
            return dc.fetch_coverage(), "dealcloud", None
        except Exception as e:  # noqa: BLE001
            banner = f"DealCloud unavailable — using uploaded Excel ({e})"
            if uploaded_excel_path:
                return read_dealcloud_excel(uploaded_excel_path), "excel", banner
            return [], "none", banner
    if uploaded_excel_path:
        return read_dealcloud_excel(uploaded_excel_path), "excel", None
    return [], "none", "No DealCloud credentials and no Deal_CLoud.xlsx uploaded."
