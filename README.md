# SEC EDGAR Entity Resolver

Resolve companies to SEC CIK numbers, search SEC filings, and extract structured XBRL financial facts from EDGAR. No API key required. MCP-ready for AI agent integration.

## What does it do?

SEC EDGAR Entity Resolver turns company names, stock tickers, and CIK numbers into structured SEC data. It queries the SEC's public EDGAR APIs and returns clean, normalized results ready for analysis, compliance workflows, or AI agent consumption via MCP.

**Use cases:**

- **Entity resolution** -- ground company names to official SEC identifiers (CIK numbers) for downstream data pipelines
- **Due diligence** -- pull company profiles with SIC codes, addresses, fiscal year end, and filing history
- **Compliance monitoring** -- search SEC filings by form type, date range, and keyword to track regulatory submissions
- **Financial analysis** -- extract structured XBRL facts (revenue, assets, liabilities) from company filings
- **AI agent tooling** -- expose as an MCP tool so AI agents can look up SEC data in real time
- **Investment research** -- monitor 10-K, 10-Q, 8-K, and other filings for companies or industries

## Features

- **3 modes:** `resolve_entity`, `search_filings`, `get_company_facts`
- **No API key required** -- all data comes from public SEC EDGAR endpoints
- **No proxies needed** -- direct API access to government infrastructure
- **Ticker preload** -- loads SEC `company_tickers.json` for fast ticker-to-CIK resolution
- **Polite rate limiting** -- default 0.3s between requests; retry with exponential backoff on 429/5xx
- **State persistence** -- survives Apify actor migrations mid-run
- **Batch push** -- outputs in batches of 25 for efficiency
- **Free tier** -- 25 results per run without a subscription

## What data does it extract?

### Entities (resolve_entity)

| Field | Description |
|-------|-------------|
| `schema_version` | Schema version (currently `"1.0"`) |
| `type` | Always `"entity"` |
| `cik` | 10-digit SEC CIK number |
| `name` | Official company name |
| `tickers` | Stock ticker symbols |
| `sic` | SIC industry code |
| `sic_description` | SIC industry description |
| `state` | State of incorporation |
| `country` | Country of incorporation |
| `fiscal_year_end` | Fiscal year end (MMDD) |
| `mailing_address` | Mailing address |
| `business_address` | Business address |
| `former_names` | Previous company names |
| `recent_filings` | Recent SEC filings (form, date, accession number, URLs) |
| `source_urls` | SEC API URLs used |

### Filings (search_filings)

| Field | Description |
|-------|-------------|
| `schema_version` | Schema version (currently `"1.0"`) |
| `type` | Always `"filing"` |
| `cik` | Filer CIK number |
| `name` | Filer name |
| `tickers` | Filer ticker symbols |
| `form` | Form type (10-K, 10-Q, 8-K, etc.) |
| `file_date` | Filing date |
| `acceptance_datetime` | SEC acceptance timestamp |
| `accession_number` | Unique filing accession number |
| `filing_url` | Link to filing index page |
| `primary_document_url` | Link to primary document |
| `items` | Filing items (for 8-K) |
| `state` | Filer state |
| `sic` | Filer SIC code |
| `sic_description` | Filer SIC description |

### Facts (get_company_facts)

| Field | Description |
|-------|-------------|
| `schema_version` | Schema version (currently `"1.0"`) |
| `type` | Always `"fact"` |
| `cik` | Company CIK number |
| `name` | Company name |
| `sic` | SIC code |
| `concept` | XBRL concept name (e.g., `Revenue`, `Assets`) |
| `namespace` | XBRL namespace (e.g., `us-gaap`) |
| `label` | Human-readable concept label |
| `unit` | Unit of measurement (e.g., `USD`, `shares`) |
| `value` | Reported value |
| `start` | Period start date (duration facts) |
| `end` | Period end date |
| `form` | Source form type |
| `frame` | XBRL reporting frame (e.g., `CY2025Q1`) |
| `filing_url` | Link to source filing |

---

## Input

### Mode 1: Resolve Entity

Resolve a company name, ticker, or CIK to a full SEC entity profile with recent filings.

```json
{
    "mode": "resolve_entity",
    "query": "NVIDIA",
    "maxRecentFilings": 10,
    "userAgent": "YourName your-email@example.com"
}
```

Resolve by ticker:

```json
{
    "mode": "resolve_entity",
    "ticker": "AAPL",
    "maxRecentFilings": 5,
    "userAgent": "YourName your-email@example.com"
}
```

### Mode 2: Search Filings

Search SEC filings by keyword, company, form type, and date range.

```json
{
    "mode": "search_filings",
    "query": "artificial intelligence",
    "formTypes": ["10-K", "10-Q"],
    "dateFrom": "2025-01-01",
    "dateTo": "2026-01-01",
    "maxResults": 100,
    "userAgent": "YourName your-email@example.com"
}
```

Search by ticker and form prefix:

```json
{
    "mode": "search_filings",
    "ticker": "TSLA",
    "formPrefix": "8-",
    "maxResults": 50,
    "userAgent": "YourName your-email@example.com"
}
```

### Mode 3: Get Company Facts

Pull structured XBRL financial data for a company.

```json
{
    "mode": "get_company_facts",
    "ticker": "MSFT",
    "namespaces": ["us-gaap"],
    "concepts": ["Revenue", "Assets"],
    "maxResults": 200,
    "userAgent": "YourName your-email@example.com"
}
```

### Input Reference

**Common fields:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `mode` | `resolve_entity` | `resolve_entity`, `search_filings`, or `get_company_facts` |
| `query` | | Company name, ticker, CIK, or search text |
| `cik` | | 10-digit CIK (zero-padded if shorter) |
| `ticker` | | Stock ticker symbol |
| `userAgent` | | SEC-required User-Agent: `"YourName email@example.com"` |
| `maxResults` | `100` | Max results (1-1000; free tier capped at 25) |
| `requestIntervalSecs` | `0.3` | Seconds between requests |
| `timeoutSecs` | `30` | HTTP timeout |
| `maxRetries` | `5` | Retries on failure |

**resolve_entity fields:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `maxRecentFilings` | `10` | Recent filings to include (1-100) |
| `includeAmendments` | `true` | Include amended forms (*/A) |
| `formPrefix` | | Filter filings by prefix (e.g., `10-`) |

**search_filings fields:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `formTypes` | | List of forms: `10-K`, `10-Q`, `8-K`, etc. |
| `formPrefix` | | Prefix filter (e.g., `10-` matches 10-K, 10-Q) |
| `includeAmendments` | `true` | Include amended forms (*/A) |
| `dateFrom` | | Filed on or after (YYYY-MM-DD) |
| `dateTo` | | Filed on or before (YYYY-MM-DD) |
| `start` | `0` | Pagination offset |

**get_company_facts fields:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `namespaces` | | XBRL namespaces (e.g., `us-gaap`, `dei`) |
| `concepts` | | Concept names (e.g., `Revenue`, `Assets`) |
| `periodType` | | `instant` or `duration` |

---

## Output

Results are saved to the default dataset. Download them in JSON, CSV, Excel, or XML from the Output tab.

### Example: Entity output

```json
{
    "schema_version": "1.0",
    "type": "entity",
    "cik": "0001045810",
    "name": "NVIDIA CORP",
    "tickers": ["NVDA"],
    "sic": "3674",
    "sic_description": "Semiconductors & Related Devices",
    "state": "DE",
    "country": "US",
    "fiscal_year_end": "0128",
    "mailing_address": {"street1": "2788 SAN TOMAS EXPRESSWAY", "city": "SANTA CLARA", "state": "CA", "zip": "95051"},
    "business_address": {"street1": "2788 SAN TOMAS EXPRESSWAY", "city": "SANTA CLARA", "state": "CA", "zip": "95051"},
    "former_names": [],
    "recent_filings": [
        {
            "form": "10-K",
            "fileDate": "2026-02-01",
            "accessionNumber": "0001045810-26-000123",
            "filingUrl": "https://www.sec.gov/Archives/edgar/data/...",
            "primaryDocumentUrl": "https://www.sec.gov/Archives/edgar/data/..."
        }
    ],
    "source_urls": ["https://data.sec.gov/submissions/CIK0001045810.json"]
}
```

### Example: Filing output

```json
{
    "schema_version": "1.0",
    "type": "filing",
    "cik": "0001318605",
    "name": "TESLA INC",
    "tickers": ["TSLA"],
    "form": "8-K",
    "file_date": "2026-01-15",
    "acceptance_datetime": "2026-01-15T16:30:00.000Z",
    "accession_number": "0001318605-26-000456",
    "filing_url": "https://www.sec.gov/Archives/edgar/data/...",
    "primary_document_url": "https://www.sec.gov/Archives/edgar/data/...",
    "items": ["2.02", "9.01"],
    "state": "TX",
    "sic": "3711",
    "sic_description": "Motor Vehicles & Passenger Car Bodies"
}
```

### Example: Fact output

```json
{
    "schema_version": "1.0",
    "type": "fact",
    "cik": "0000789019",
    "name": "MICROSOFT CORP",
    "sic": "7372",
    "concept": "Revenue",
    "namespace": "us-gaap",
    "label": "Revenue from Contract with Customer, Excluding Assessed Tax",
    "unit": "USD",
    "value": 56189000000,
    "start": "2025-07-01",
    "end": "2025-09-30",
    "form": "10-Q",
    "frame": "CY2025Q3",
    "filing_url": "https://www.sec.gov/Archives/edgar/data/..."
}
```

---

## Cost

This actor uses **pay-per-event (PPE) pricing**. You pay only for the results you get.

- **$0.50 per 1,000 results** ($0.0005 per result)
- **No proxy costs** -- public government APIs
- **No API key costs** -- SEC EDGAR is free and public
- Free tier: **25 results per run** (no subscription required)

---

## Technical details

- SEC EDGAR EFTS API (`efts.sec.gov/LATEST/search-index`) for full-text filing search
- SEC EDGAR Submissions API (`data.sec.gov/submissions/`) for entity profiles and recent filings
- SEC EDGAR XBRL CompanyFacts API (`data.sec.gov/api/xbrl/companyfacts/`) for structured financial data
- SEC company tickers file (`sec.gov/files/company_tickers.json`) preloaded for fast ticker resolution
- SEC requires a `User-Agent` header with name and email on all requests
- Rate limited to 1 request per 0.3 seconds (configurable)
- Automatic retry with exponential backoff and jitter on failures
- Results pushed in batches of 25 for efficiency
- Actor state persisted across migrations
- No proxies, no browser, no cookies -- direct API access

---

## MCP Integration

This actor works as an MCP tool through Apify's hosted MCP server. No custom server needed.

- **Endpoint:** `https://mcp.apify.com?tools=labrat011/sec-edgar-scraper`
- **Auth:** `Authorization: Bearer <APIFY_TOKEN>`
- **Transport:** Streamable HTTP
- **Works with:** Claude Desktop, Cursor, VS Code, Windsurf, Warp, Gemini CLI

**Example MCP config (Claude Desktop / Cursor):**

```json
{
    "mcpServers": {
        "sec-edgar-scraper": {
            "url": "https://mcp.apify.com?tools=labrat011/sec-edgar-scraper",
            "headers": {
                "Authorization": "Bearer <APIFY_TOKEN>"
            }
        }
    }
}
```

AI agents can use this actor to resolve company names to CIK numbers, search SEC filings, and pull structured XBRL financial data -- all as a callable MCP tool.

---

## FAQ

### Do I need an API key?

No. SEC EDGAR is a public government data source with no authentication. You do need to provide a `User-Agent` header (name and email) per SEC's fair access policy.

### What is a CIK?

A Central Index Key (CIK) is the SEC's unique identifier for every entity that files with the commission. Think of it as an SEC serial number for companies.

### Can I combine filters?

Yes. For filing search, combine keyword + form types + date range + ticker/CIK. All filters are AND-combined.

### What XBRL namespaces are available?

The most common are `us-gaap` (US financial reporting standards) and `dei` (document and entity information). Some companies also report under `ifrs-full` (international standards).

---

## Feedback

Found a bug or have a feature request? Open an issue on the actor's Issues tab in Apify Console.
