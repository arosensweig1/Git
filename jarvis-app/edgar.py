"""EDGAR (SEC) helpers — public filings, no API key required.

Used to back 'Last financing' transaction documents (prospectus + 8-K/6-K) and
to supplement Cap IQ. SEC asks for a descriptive User-Agent on every request.

  * company tickers -> CIK : https://www.sec.gov/files/company_tickers.json
  * recent filings (by CIK): https://data.sec.gov/submissions/CIK##########.json
  * full-text search       : https://efts.sec.gov/LATEST/search-index?q=...
"""
import requests

# Set this to your firm contact per SEC fair-access policy.
UA = {"User-Agent": "AGP-Jarvis ECM tool (contact: ops@agp.com)"}

PROSPECTUS_FORMS = ("424B5", "424B3", "424B4", "S-1", "S-3", "F-1")
TRANSACTION_FORMS = ("8-K", "6-K")

_TICKER_CACHE = {}


def ticker_to_cik(ticker):
    """Map a ticker to a zero-padded 10-digit CIK string (cached)."""
    if not _TICKER_CACHE:
        r = requests.get("https://www.sec.gov/files/company_tickers.json",
                         headers=UA, timeout=30)
        r.raise_for_status()
        for row in r.json().values():
            _TICKER_CACHE[row["ticker"].upper()] = str(row["cik_str"]).zfill(10)
    return _TICKER_CACHE.get((ticker or "").upper())


def _doc_url(cik_int, accession, doc):
    return (f"https://www.sec.gov/Archives/edgar/data/{cik_int}/"
            f"{accession.replace('-', '')}/{doc}")


def recent_filings(ticker, forms=None, limit=10):
    """Return recent filings for a ticker as
    [{form, date, accession, url, primary_doc}]. forms optionally filters."""
    cik = ticker_to_cik(ticker)
    if not cik:
        return []
    r = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json",
                     headers=UA, timeout=30)
    r.raise_for_status()
    recent = r.json().get("filings", {}).get("recent", {})
    cik_int = int(cik)
    forms_u = {f.upper() for f in forms} if forms else None
    out = []
    for form, date, acc, doc in zip(recent.get("form", []),
                                    recent.get("filingDate", []),
                                    recent.get("accessionNumber", []),
                                    recent.get("primaryDocument", [])):
        if forms_u and form.upper() not in forms_u:
            continue
        out.append({"form": form, "date": date, "accession": acc,
                    "primary_doc": doc, "url": _doc_url(cik_int, acc, doc)})
        if len(out) >= limit:
            break
    return out


def financing_docs(ticker):
    """Best-effort latest prospectus + latest transaction doc (8-K/6-K)."""
    pros = recent_filings(ticker, PROSPECTUS_FORMS, limit=1)
    trans = recent_filings(ticker, TRANSACTION_FORMS, limit=1)
    return {
        "prospectus": pros[0] if pros else None,
        "transaction": trans[0] if trans else None,
    }


def full_text_search(query, forms=None, limit=10):
    """EDGAR full-text search (last ~10 years). Returns [{form, date, url}]."""
    params = {"q": f'"{query}"'}
    if forms:
        params["forms"] = ",".join(forms)
    r = requests.get("https://efts.sec.gov/LATEST/search-index",
                     params=params, headers=UA, timeout=30)
    r.raise_for_status()
    hits = r.json().get("hits", {}).get("hits", [])
    out = []
    for h in hits[:limit]:
        src = h.get("_source", {})
        cik = (src.get("ciks") or ["0"])[0]
        acc, _, doc = h.get("_id", "").partition(":")
        out.append({"form": src.get("file_type") or (src.get("root_forms") or [""])[0],
                    "date": src.get("file_date"),
                    "url": _doc_url(int(cik), acc, doc) if acc and doc else None})
    return out
