"""Target-list construction. Source-agnostic: `universe_rows` are Cap IQ saved-screen
constituents. Logic is the PART 7 reference implementation, used verbatim."""
from datetime import datetime
from dateutil.relativedelta import relativedelta
import re

REGION_SUFFIX_RE = re.compile(r"-[A-Z]{2}$")


def normalize_ticker(ticker):
    if ticker is None:
        return None
    t = str(ticker).strip().upper()
    if not t:
        return None
    t = REGION_SUFFIX_RE.sub("", t)   # strip trailing -US, -GB, -CA, etc.
    return t or None


def normalize_name(name):
    if name is None:
        return None
    n = re.sub(r"\s+", " ", str(name).strip().lower())
    return n or None


def _make_key(nt, nn):
    if nt:
        return "tk:" + nt
    if nn:
        return "nm:" + nn
    return None


def build_target_list(crm_rows, universe_rows, months_threshold=24,
                      market_cap_cap=500_000_000, today=None):
    """
    crm_rows: dicts with keys company, exchange, ticker, banker, date_of_outreach (datetime or None)
    universe_rows: dicts with keys company/companyName/name, ticker/symbol, exchange, market_cap, price
                   (Cap IQ saved-screen constituents, already < cap on NASDAQ/NYSE/AMEX)
    Returns: list of final outreach dicts.
    """
    if today is None:
        today = datetime.now()
    cutoff = today - relativedelta(months=months_threshold)

    set_a = {}
    blocked_tickers = set()
    blocked_names = set()

    # Classify CRM rows. Any outreach within the window => company is covered (blocked).
    for r in crm_rows:
        d = r.get("date_of_outreach")
        if d is None:
            continue
        nt = normalize_ticker(r.get("ticker"))
        nn = normalize_name(r.get("company"))
        key = _make_key(nt, nn)
        if key is None:
            continue
        if d < cutoff:
            set_a[key] = {
                "ticker": r.get("ticker"),
                "norm_ticker": nt,
                "norm_name": nn,
                "company": r.get("company"),
                "exchange": r.get("exchange"),
                "source_set": "A",
                "reason": f"CRM revival: last outreach {d.strftime('%m/%d/%Y')} (> {months_threshold} months)",
                "last_outreach": d,
                "banker": r.get("banker"),
            }
        else:
            if nt: blocked_tickers.add(nt)
            if nn: blocked_names.add(nn)

    # A company contacted recently in ANY row is covered even if another row is old.
    for key in list(set_a.keys()):
        rec = set_a[key]
        if (rec["norm_ticker"] and rec["norm_ticker"] in blocked_tickers) or \
           (rec["norm_name"] and rec["norm_name"] in blocked_names):
            del set_a[key]

    final = dict(set_a)

    # Set B: Cap IQ screen universe, minus blocked, merged with Set A.
    for u in universe_rows:
        nt = normalize_ticker(u.get("ticker") or u.get("symbol"))
        nn = normalize_name(u.get("company") or u.get("companyName") or u.get("name"))
        key = _make_key(nt, nn)
        if key is None:
            continue
        if (nt and nt in blocked_tickers) or (nn and nn in blocked_names):
            continue
        if key in final:
            final[key]["source_set"] = "both"
            final[key]["reason"] += f"; also sub-${market_cap_cap:,.0f} {u.get('exchange','')}".rstrip()
        else:
            final[key] = {
                "ticker": u.get("ticker") or u.get("symbol"),
                "norm_ticker": nt,
                "norm_name": nn,
                "company": u.get("company") or u.get("companyName") or u.get("name"),
                "exchange": u.get("exchange"),
                "source_set": "B",
                "reason": f"Sub-${market_cap_cap:,.0f} {u.get('exchange','')} small-cap".rstrip(),
                "last_outreach": None,
                "banker": None,
            }

    return list(final.values())
