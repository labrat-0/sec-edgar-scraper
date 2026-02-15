# SEC EDGAR Entity Resolver

Resolve companies to SEC CIKs, search filings, and pull XBRL facts from EDGAR. No API key required.

## What does it do?

This actor provides three EDGAR utilities in one:
- **Resolve entities**: Company name/ticker/CIK → normalized entity profile (CIK, SIC, addresses, fiscal year end, tickers, former names) plus recent filings.
- **Search filings**: Full-text filing search with form/date filters and direct links to filings and primary documents.
- **Get company facts**: Structured XBRL facts by CIK with optional namespace/concept/period filters.

## Features

- **3 modes:** `resolve_entity`, `search_filings`, `get_company_facts`
- **No API key required** — public SEC data
- **Polite rate limiting** — default 0.3s between requests; retry/backoff on 429/5xx
- **Ticker preload** — uses SEC `company_tickers.json` for ticker→CIK mapping
- **State persistence** — survives Apify actor migrations mid-run
- **Batch push** — outputs in batches of 25
- **Free tier** — caps to 25 results when running on Apify without a paid user

## Input

```json
{
  "mode": "resolve_entity",
  "query": "NVIDIA",
  "maxRecentFilings": 10,
  "requestIntervalSecs": 0.3
}
```

### Common fields
- `mode`: `resolve_entity` | `search_filings` | `get_company_facts`
- `query`: Company name/ticker/CIK for resolve; text for filings search
- `cik`: 10-digit CIK (unpadded accepted)
- `ticker`: Stock ticker
- `maxResults`: Default 100 (capped to 25 on free tier)
- `requestIntervalSecs`: Default 0.3s between requests
- `timeoutSecs`: Default 30
- `maxRetries`: Default 5

### resolve_entity
- `query`, `ticker`, or `cik` (one required)
- `maxRecentFilings`: default 10 (1–100)
- `includeAmendments`: default true
- `formPrefix`: optional prefix filter (e.g., `10-`)

### search_filings
- `query`: text search
- `cik` or `ticker`: optional; narrows results
- `formTypes`: list of forms (e.g., `10-K`, `10-Q`, `8-K`)
- `formPrefix`: optional prefix (e.g., `10-`)
- `includeAmendments`: default true (if false, filters `*/A`)
- `dateFrom` / `dateTo`: YYYY-MM-DD
- `start`: offset; `maxResults`: cap (default 100, hard cap 1000; free tier 25)

### get_company_facts
- `cik` or `ticker`: required
- Optional filters: `namespaces` (e.g., `us-gaap`), `concepts`, `periodType` (`instant` | `duration`)

## Output

- `resolve_entity`: type=`entity`, `cik`, `name`, `tickers`, `sic`, `sicDescription`, `state`, `country`, `fiscalYearEnd`, `mailingAddress`, `businessAddress`, `formerNames`, `recentFilings` (form, fileDate, accessionNumber, filingUrl, primaryDocumentUrl), `sourceUrls`.
- `search_filings`: type=`filing`, `cik`, `name`, `tickers`, `form`, `fileDate`, `acceptanceDatetime`, `accessionNumber`, `filingUrl`, `primaryDocumentUrl`, `items`, `state`, `sic`, `sicDescription`.
- `get_company_facts`: type=`fact`, `cik`, `name`, `sic`, `concept`, `namespace`, `label`, `unit`, `value`, `start`, `end`, `form`, `frame`, `filingUrl`.

## Pricing

- `$0.0005/result` with a **free tier of 25 results per run** on Apify.

## MCP note

Any Apify actor can be exposed as an MCP tool via `https://mcp.apify.com?tools=<actor-id>` with `Authorization: Bearer <APIFY_TOKEN>`. This actor follows the same pattern; no custom server needed. Rate limit remains ~30 req/s per user; keep the default 0.3s interval unless you know you need more throughput.
