# Jarvis — Live Data Integration Setup

> **Status: WAITING ON CREDENTIALS / FIELD NAMES.**
> This doc captures everything needed to connect real Capital IQ + DealCloud
> data to Jarvis. When the rep info comes back, follow "When the info arrives"
> at the bottom. Nothing secret lives in this file (and nothing secret ever
> should — see the security note).

---

## Where things stand

- **Static demo** (no login, boots straight into the terminal):
  `https://raw.githack.com/arosensweig1/Git/claude/quirky-ramanujan-Kuzo3/demo/jarvis/index.html`
  Runs on fake data. Cannot hold credentials or pull live data — that's by design.
- **Runnable app** (`jarvis-app/`): the only way to use real credentials and pull
  live data. Run locally: `streamlit run app.py` → `http://localhost:8501`.
  Its **"Verify connection & pulls"** page is the "is everything working?" check.
- **Blocked on:** the two requests below (API credentials + confirmed field
  names/mnemonics). I deliberately did not guess these.

---

## What to do with the answers (the two fill-in points)

1. **Credentials** → `jarvis-app/.env` (copy from `.env.example`; `.env` is gitignored, never committed).
2. **Confirmed Cap IQ mnemonics** → `CAPIQ_FIELD_MAP` in `jarvis-app/data_market.py`
   (replace every `IQ_PLACEHOLDER_*` and confirm the others).
   **Confirmed DealCloud field names** → `DC_*` vars in `jarvis-app/data_crm.py` / `.env`.
3. Run the **Verify connection & pulls** page → green per field = working.

---

## 1) Capital IQ — what was requested

**API access:**
- Cap IQ **GDS API** (Web Services Direct / GDSP REST), not the web portal
- Credentials: API username/password **or** API key/token
- Exact **base URL** for the entitlement
  (app default: `https://api-ciq.marketintelligence.spglobal.com/gdsapi/rest/v3/clientservice.json`)
- **Screening / saved-list expansion** over the API (for the "Set B" universe; app uses `CAPIQ_UNIVERSE_SCREEN_ID`)

**Data fields / entitlements** (dashboard field → likely mnemonic, confirm against data dictionary):

| Category | Dashboard fields | Likely mnemonic (confirm) |
|---|---|---|
| Reference | company name, exchange, sector, website, description | `IQ_COMPANY_NAME_LONG`, `IQ_EXCHANGE`, `IQ_PRIMARY_INDUSTRY`, `IQ_COMPANY_WEBSITE`, `IQ_BUSINESS_DESCRIPTION` |
| Market data | market cap, last price, 1-day % change | `IQ_MARKETCAP`, `IQ_LASTSALEPRICE`, `IQ_PRICE_CHANGE_1D` |
| Pricing time-series | close, VWAP, volume (date-ranged: 1D/1W/1M/3M/6M/1Y, 5-day VWAP) | `IQ_CLOSEPRICE`, `IQ_VWAP`, `IQ_VOLUME` |
| Financials | cash & equivalents, total debt, trailing-12mo cash from operations (for burn/runway) | `IQ_CASH_EQUIV`, `IQ_TOTAL_DEBT`, `IQ_CASH_OPER` (LTM) |
| Key People (Professionals) | CEO name, CFO name | (Professionals package — ask rep) |
| Ownership | top institutional / 13F holders | (Ownership package) |
| Estimates / Research | price target high/low/avg, consensus rating, covering analysts/banks | `IQ_PRICETARGET_HIGH/LOW/AVG`, `IQ_RATING_CONSENSUS`, research-providers field |
| News | recent headlines | (News package) |

**Entitlement packages to confirm:** Market Data, Estimates/Consensus, Ownership,
Key People (Professionals), News, Screening/Lists.

**Cash burn / runway:** no single mnemonic — derived.
`runway months = (cash − total debt) ÷ (12-mo cash burn ÷ 12)`.
Need trailing-12mo cash from operations (and capex for free-cash-burn).

---

## 2) DealCloud — what was requested

**API access:**
- Registered **API service account / OAuth2 application** → **Client ID** + **Client Secret** (OAuth2 client-credentials grant)
- **Read ("data" scope)** access to the **Company** entity
- Site / API base URL (e.g. `https://yourfirm.dealcloud.com`)

**Fields needed (exact API names — site-specific):**

| What Jarvis reads | Typical field (confirm exact API name) | Code var |
|---|---|---|
| Company object/entity | `Company` | `DC_COMPANY_OBJECT` |
| Company name | `CompanyName` / `Name` | — |
| Ticker | `Ticker` / `TickerSymbol` | — |
| Exchange | `Exchange` | — |
| Covering banker | `CoveringBanker` | `DC_BANKER_FIELD` |
| Date of last outreach (drives 24-mo revival rule) | `LastOutreach` | `DC_LAST_OUTREACH_FIELD` |

**Excel fallback (no API needed):** `Deal_CLoud.xlsx` with header on **row 3**,
columns: `Company Name`, `Exchange`, `Ticker Symbol` (or `Ticker`), `Banker`, `Date of Outreach`.

---

## Draft emails (sent to reps — kept for reference)

### To S&P / Capital IQ rep
> **Subject:** Capital IQ API access request — credentials + data entitlements for an internal tool
>
> Hi [Rep name],
>
> I'm building an internal prospecting dashboard at [Firm name] and need to pull Capital IQ data programmatically via the **GDS API (Web Services Direct / GDSP REST service)** — not the web portal. Could you help me get the following set up, and send back the details noted at the bottom?
>
> **1. API access & credentials**
> - Access to the Cap IQ **GDS API** for our entitlement
> - API **credentials** — username/password or an API key/token (whichever our entitlement uses)
> - The exact **base URL / endpoint** for our account
> - **Screening / saved-list expansion** over the API, so I can pull a screen I build in Cap IQ Pro (I'll reference it by screen ID)
>
> **2. Data entitlements** — please confirm we're entitled to these packages over the API, and send the exact **mnemonics / field codes** for each:
> - **Reference:** company name, exchange, primary industry/sector, website, business description
> - **Market data:** market cap, last sale price, 1-day % change
> - **Pricing time-series:** historical close price, VWAP, and volume (date-ranged, so I can show 1D/1W/1M/3M/6M/1Y and a 5-day VWAP)
> - **Financials:** cash & equivalents, total debt, and trailing-12-month **cash flow from operations** (I'm deriving a cash-burn / runway figure)
> - **Key People (Professionals):** CEO and CFO names
> - **Ownership:** top institutional / 13F holders
> - **Estimates / Research:** consensus price target (high / low / avg), consensus rating, and the **list of analysts/banks providing coverage**
> - **News:** recent company headlines
>
> **What I need back from you:**
> 1. The API credentials (and whether it's user/pass or API key)
> 2. The base URL/endpoint for our entitlement
> 3. Confirmation of which of the above packages we're entitled to
> 4. The exact mnemonics/field codes (or a link to the current data dictionary)
>
> Happy to hop on a quick call if that's easier. Thanks very much for the help.
>
> Best,
> [Your name] / [Title], [Firm name] / [Phone]

### To DealCloud admin / rep
> **Subject:** DealCloud API access request — OAuth credentials + Company field names for an internal tool
>
> Hi [Admin/Rep name],
>
> I'm connecting an internal dashboard to DealCloud to read our coverage data via the **REST API** (OAuth2 client-credentials). Could you help me get the following provisioned and send back the details at the bottom?
>
> **1. API access & credentials**
> - A registered **API service account / OAuth2 application** with a **Client ID** and **Client Secret**
> - **Read access ("data" scope)** to our **Company** entity
> - Our **site / API base URL** (e.g. `https://[ourfirm].dealcloud.com`)
>
> **2. Field names** — I need the exact **API field names** (not just the display labels) for these on the Company object:
> - Company name
> - Ticker symbol
> - Exchange
> - **Covering banker**
> - **Date of last outreach** (this drives a "revisit after 24 months" rule, so it's important)
>
> **What I need back from you:**
> 1. Client ID + Client Secret
> 2. Our site/API base URL
> 3. The exact API name of the **Company** object and the five fields above
>
> If API provisioning will take a while, a quick interim option: an **Excel export** of the company list with columns `Company Name`, `Exchange`, `Ticker Symbol`, `Banker`, `Date of Outreach` would let me start testing immediately — but the API is the goal.
>
> Thanks so much,
> [Your name] / [Title], [Firm name] / [Phone]

---

## ⚠️ Security note (read before sending credentials back)

When the reps reply, **do NOT paste API keys, passwords, or client secrets into
chat or into any committed file.** Those go ONLY into local `jarvis-app/.env`
(gitignored). Safe to share for wiring up: **base URLs, confirmed field
names/mnemonics, and which entitlements were granted.** No secrets required to
update `CAPIQ_FIELD_MAP` and the `DC_*` fields.

---

## When the info arrives — checklist for the next session

- [ ] Cap IQ: base URL confirmed
- [ ] Cap IQ: auth type (user/pass vs API key) confirmed
- [ ] Cap IQ: entitlement packages confirmed (Market Data, Estimates, Ownership, Professionals, News, Screening)
- [ ] Cap IQ: real mnemonics received → update `CAPIQ_FIELD_MAP` in `data_market.py`
- [ ] Cap IQ: saved-screen ID for Set B universe
- [ ] DealCloud: Client ID + Secret obtained (→ local `.env` only)
- [ ] DealCloud: site/API base URL confirmed
- [ ] DealCloud: exact Company object + 5 field API names → update `DC_*` vars
- [ ] Credentials placed in local `jarvis-app/.env`
- [ ] Ran "Verify connection & pulls" → all fields green
