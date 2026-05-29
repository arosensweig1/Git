"""Capital IQ — the SOLE market-data source.

This wraps the Cap IQ "GDS" REST endpoint (Web Service Direct). The API is
mnemonic/identifier based and entitlement-gated, so:

  * DO NOT trust the placeholder mnemonics below blindly — paste the exact
    mnemonics your S&P entitlement supports into CAPIQ_FIELD_MAP and confirm
    the request functions/endpoint against the S&P API docs.
  * Every field is fetched defensively: entitlement errors are caught and the
    field is marked "Cap IQ: not entitled" rather than crashing the app.

The connection-test (`connection_test`) is what you run first to confirm that
your credentials authenticate and which mapped fields actually return data.
"""
import os
import time
import requests

# ----------------------------------------------------------------------------
# Field map: dashboard field  ->  Cap IQ mnemonic.
# Replace every "IQ_PLACEHOLDER_*" with the exact mnemonic you are entitled to.
# Confirm names/casing against the S&P Capital IQ data dictionary.
# ----------------------------------------------------------------------------
CAPIQ_FIELD_MAP = {
    "company_name":        "IQ_COMPANY_NAME_LONG",      # confirm
    "exchange":            "IQ_EXCHANGE",               # confirm
    "market_cap":          "IQ_MARKETCAP",              # confirm
    "price":               "IQ_LASTSALEPRICE",          # confirm
    "price_change":        "IQ_PRICE_CHANGE_1D",        # confirm
    "sector":              "IQ_PRIMARY_INDUSTRY",       # confirm
    "website":             "IQ_COMPANY_WEBSITE",        # confirm
    "description":         "IQ_BUSINESS_DESCRIPTION",   # confirm
    "ceo_name":            "IQ_PLACEHOLDER_CEO",        # Professionals data — confirm
    "cfo_name":            "IQ_PLACEHOLDER_CFO",        # Professionals data — confirm
    "close_series":        "IQ_CLOSEPRICE",             # time-series; confirm period args
    "vwap_series":         "IQ_VWAP",                   # time-series; confirm
    "volume_series":       "IQ_VOLUME",                 # time-series; confirm
    "cash":                "IQ_CASH_EQUIV",             # confirm
    "total_debt":          "IQ_TOTAL_DEBT",             # confirm
    "cash_burn_ltm":       "IQ_PLACEHOLDER_BURN_LTM",   # derive if no direct mnemonic
    "top_holders":         "IQ_PLACEHOLDER_HOLDERS",    # ownership; confirm
    "news":                "IQ_PLACEHOLDER_NEWS",       # news; confirm
    "pt_high":             "IQ_PRICETARGET_HIGH",       # confirm
    "pt_low":              "IQ_PRICETARGET_LOW",        # confirm
    "pt_avg":              "IQ_PRICETARGET_AVG",        # confirm
    "consensus_rating":    "IQ_RATING_CONSENSUS",       # confirm
}


class CapIQError(Exception):
    pass


class CapIQProvider:
    ENTITLEMENT_MARKERS = ("NOT ENTITLED", "ENTITLEMENT NEEDED", "CAPABILITY NEEDED")

    def __init__(self, base_url=None, username=None, password=None, api_key=None):
        self.base_url = base_url or os.getenv("CAPIQ_BASE_URL", "")
        self.username = username or os.getenv("CAPIQ_USERNAME", "")
        self.password = password or os.getenv("CAPIQ_PASSWORD", "")
        self.api_key = api_key or os.getenv("CAPIQ_API_KEY", "")
        self.screen_id = os.getenv("CAPIQ_UNIVERSE_SCREEN_ID", "")
        self._session = requests.Session()

    def configured(self):
        return bool(self.base_url and (self.username and self.password or self.api_key))

    # -- low-level GDS request -------------------------------------------------
    def _request(self, input_requests, retries=3):
        """input_requests: list of {"function","identifier","mnemonic","properties"?}."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            auth = None
        else:
            auth = (self.username, self.password)
        body = {"inputRequests": input_requests}
        last = None
        for attempt in range(retries):
            try:
                resp = self._session.post(self.base_url, json=body, headers=headers,
                                          auth=auth, timeout=45)
                if resp.status_code in (429, 503):       # throttled — back off
                    time.sleep(2 ** attempt)
                    last = f"HTTP {resp.status_code}"
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                last = str(e)
                time.sleep(2 ** attempt)
        raise CapIQError(f"Cap IQ request failed after {retries} tries: {last}")

    def _is_entitlement_error(self, val):
        if val is None:
            return False
        s = str(val).upper()
        return any(m in s for m in self.ENTITLEMENT_MARKERS)

    def fetch_field(self, identifier, mnemonic, properties=None):
        """Fetch one mnemonic for one identifier. Returns (value, status)."""
        req = {"function": "GDSP", "identifier": identifier, "mnemonic": mnemonic}
        if properties:
            req["properties"] = properties
        try:
            data = self._request([req])
        except CapIQError as e:
            return None, f"error: {e}"
        try:
            rows = data["GDSSDKResponse"][0]["Rows"]
            val = rows[0]["Row"][0]
        except (KeyError, IndexError, TypeError):
            return None, "no data"
        if self._is_entitlement_error(val):
            return None, "Cap IQ: not entitled"
        return val, "ok"

    # -- health / connection test ---------------------------------------------
    def authenticate_test(self, probe_identifier="IBM:"):
        """Cheap call to confirm credentials authenticate at all."""
        try:
            self._request([{"function": "GDSP", "identifier": probe_identifier,
                            "mnemonic": CAPIQ_FIELD_MAP["company_name"]}])
            return True, "Authenticated — Cap IQ accepted the credentials."
        except CapIQError as e:
            return False, f"Authentication / request failed: {e}"

    def connection_test(self, probe_identifier="IBM:"):
        """Run every mapped scalar field against a probe identifier and report
        which are entitled. This is the 'is everything pulling?' report."""
        ok_auth, msg = self.authenticate_test(probe_identifier)
        results = {"_auth": {"ok": ok_auth, "detail": msg}}
        if not ok_auth:
            return results
        for field, mnem in CAPIQ_FIELD_MAP.items():
            if mnem.startswith("IQ_PLACEHOLDER"):
                results[field] = {"mnemonic": mnem, "status": "placeholder — set a real mnemonic"}
                continue
            val, status = self.fetch_field(probe_identifier, mnem)
            results[field] = {"mnemonic": mnem, "status": status,
                              "sample": None if val is None else str(val)[:60]}
        return results

    # -- universe (Set B) ------------------------------------------------------
    def get_universe(self):
        """Retrieve constituents of the saved screen (CAPIQ_UNIVERSE_SCREEN_ID).
        The exact function for screen/list expansion depends on your entitlement
        (e.g. a GDSP list-identifier call). Confirm against the API docs and
        return a list of dicts: {company, ticker, exchange, market_cap, price}."""
        if not self.screen_id:
            raise CapIQError("CAPIQ_UNIVERSE_SCREEN_ID is not set.")
        # Placeholder: returns [] until the list-expansion call is confirmed for
        # your entitlement. See README 'Cap IQ saved screen'.
        return []

    # -- per-company enrichment -----------------------------------------------
    def enrich_company(self, identifier):
        """Pull every mapped field for one identifier; entitlement errors are
        captured per-field so partial data still renders."""
        out, status = {}, {}
        for field, mnem in CAPIQ_FIELD_MAP.items():
            if mnem.startswith("IQ_PLACEHOLDER"):
                out[field], status[field] = None, "placeholder"
                continue
            val, st = self.fetch_field(identifier, mnem)
            out[field], status[field] = val, st
        out["_status"] = status
        return out
