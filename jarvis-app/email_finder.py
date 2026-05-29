"""Optional executive-email supplement. OFF BY DEFAULT. Modes:
  1) hunter   — Hunter.io /v2/email-finder (returns email + confidence)
  2) pattern  — guessed first.last@/flast@/first@ on the corporate domain (UNVERIFIED)
  3) none     — blank for manual entry
Never returns a guessed address without the 'guessed' source flag; never fabricates."""
import os
import requests


def find_email(first, last, domain, mode="none"):
    """Returns (email_or_None, source_flag, confidence_or_None)."""
    if not domain or mode == "none":
        return None, "manual", None

    if mode == "hunter":
        key = os.getenv("HUNTER_API_KEY")
        if not key:
            return None, "manual", None
        try:
            r = requests.get("https://api.hunter.io/v2/email-finder",
                             params={"domain": domain, "first_name": first,
                                     "last_name": last, "api_key": key}, timeout=20)
            r.raise_for_status()
            d = r.json().get("data", {})
            if d.get("email"):
                return d["email"], "verified", d.get("score")
        except requests.RequestException:
            pass
        return None, "manual", None

    if mode == "pattern":
        f, l = (first or "").lower(), (last or "").lower()
        if not f or not l:
            return None, "manual", None
        return f"{f}.{l}@{domain}", "guessed", None   # caller must show "UNVERIFIED"

    return None, "manual", None
