# JARVIS — ECM Prospecting Terminal

Internal investment-banking prospecting terminal for A.G.P. / Alliance Global Partners.
Capital IQ is the **sole** market-data source; DealCloud (with an Excel fallback) supplies
CRM coverage. **The app never sends email** — it drafts and queues for human review only.

> ⚠️ This is internal broker-dealer tooling. Keep the deployment private/access-controlled
> and get IT/Compliance sign-off before exposing it. Never commit `.env`.

---

## 1. Run it locally (this is your "link" to test credentials)

A browser page cannot hold your Cap IQ / DealCloud credentials or call those APIs — that
must happen server-side. So to verify real data is pulling, run the app on **your own
machine** and open the local URL it prints:

```bash
cd jarvis-app
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # then edit .env (see §2)
streamlit run app.py
```

Streamlit prints a URL — open **http://localhost:8501** in your browser (bookmark it).
Login → **Connect** your sources → **Verify connection & pulls**.

## 2. Configure `.env`

1. **Website login.** Generate a password hash and paste it into `APP_USERS`:
   ```bash
   python make_hash.py 'banking590!!!' aragpjarvistest1
   # -> aragpjarvistest1:$2b$12$....   (copy the whole line into APP_USERS)
   ```
   Only the hash is stored. **Rotate this test credential before any real use.**
2. **Cap IQ API creds** — `CAPIQ_BASE_URL`, `CAPIQ_USERNAME`, `CAPIQ_PASSWORD` (or
   `CAPIQ_API_KEY`), and `CAPIQ_UNIVERSE_SCREEN_ID`. These are **API** credentials from your
   S&P rep / firm admin — *not* your capitaliq.spglobal.com web-portal password.
3. **DealCloud API creds** — `DC_SITE_URL`, `DC_CLIENT_ID`, `DC_CLIENT_SECRET` (or skip and
   upload `Deal_CLoud.xlsx` on the Connect page).
4. *(optional)* `HUNTER_API_KEY` for email enrichment, `ANTHROPIC_API_KEY` for tailored drafts.

## 3. Verify everything is pulling

Open **"Verify connection & pulls"**:
- **Run Cap IQ connection test** → authenticates and shows a per-field table of which mapped
  mnemonics are entitled (`ok` / `not entitled` / `placeholder` / `no data`) with a sample value.
- **Test CRM** → pulls DealCloud (or your uploaded Excel) and previews the rows.

Until this page shows `ok` for the fields you care about, the dashboard can't display them.

## 4. Cap IQ mnemonics & saved screen (you must supply these)

The Cap IQ API is mnemonic/identifier based and entitlement-gated. **Do not trust guessed
mnemonics.** Open `data_market.py` and replace every `IQ_PLACEHOLDER_*` (and confirm the
others) in `CAPIQ_FIELD_MAP` with the exact mnemonics your entitlement supports, per the S&P
data dictionary. Likewise confirm the request function/endpoint in `_request()`.

**Set B universe** comes from a **saved screen** you build in Cap IQ Pro (NASDAQ + NYSE +
NYSE American, market cap < $500M, primary common equity). Put its id in
`CAPIQ_UNIVERSE_SCREEN_ID` and implement the list-expansion call in
`CapIQProvider.get_universe()` (left as a confirmed-against-docs placeholder).

## 5. Target-list logic (PART 7, used verbatim)

`pipeline.build_target_list` = **(CRM revival, last outreach > `MONTHS_THRESHOLD`)** ∪
**(Cap IQ small-cap < `MARKET_CAP_CAP`)** − **(covered within the threshold)**, de-duped by
normalized ticker (region suffixes stripped) then name. Thresholds are editable in the sidebar.
The Excel parser (`data_crm.read_dealcloud_excel`) matches the reference exactly (Sheet1,
header row 3, non-breaking-space dates).

## 6. Deploy to www.agparjaarvis.com

1. **Host** on a server you control (an internal/on-prem box is preferable for compliance, or
   a small cloud VM). Start command:
   ```bash
   streamlit run app.py --server.port $PORT --server.address 0.0.0.0
   ```
2. **HTTPS/TLS** — put it behind a reverse proxy (nginx/Caddy) with a valid certificate
   (e.g. Let's Encrypt). Strongly recommended: also place it behind the firm's SSO / VPN /
   identity-aware proxy.
3. **DNS** at your registrar for `agparjaarvis.com`:
   - `A` record: `@` → your server's public IP (or `CNAME` `@`/`www` → your host's domain)
   - `CNAME` record: `www` → `agparjaarvis.com` (or the host's target)
   Then `www.agparjaarvis.com` resolves to the deployment over HTTPS.

## Files
`app.py` (gateway + pages) · `auth.py` (login) · `connections.py` (connect screen) ·
`data_market.py` (CapIQProvider + field map + connection test) · `data_crm.py` (DealCloud +
Excel parser) · `pipeline.py` (target list) · `emailer.py` (drafts/export, never sends) ·
`email_finder.py` (optional enrichment) · `make_hash.py` (password hasher).

## Limitations
API creds ≠ web-portal logins (separate SSO). Set B completeness is bounded by your saved
screen + entitlements. Holders are quarterly 13F-type. Intraday depth depends on entitlements.
Verified executive emails may require the optional enrichment provider. No market-data
fallback — if Cap IQ is unavailable, market fields show as unavailable.
