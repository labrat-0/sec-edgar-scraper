from __future__ import annotations

import logging
from typing import Any, AsyncGenerator

import httpx

from .models import EntityProfile, FactRecord, FilingRecord, ScraperInput, TickerRecord
from .utils import (
    COMPANY_FACTS_URL,
    COMPANY_TICKERS_URL,
    EFTS_SEARCH_URL,
    SUBMISSIONS_URL,
    RateLimiter,
    build_filing_url,
    build_headers,
    build_primary_doc_url,
    fetch_json,
)

logger = logging.getLogger(__name__)


class TickerCache:
    def __init__(self) -> None:
        self.loaded = False
        self.by_ticker: dict[str, TickerRecord] = {}
        self.by_cik: dict[str, list[TickerRecord]] = {}

    async def ensure(self, client: httpx.AsyncClient, headers: dict[str, str], rate_limiter: RateLimiter, timeout: float, retries: int) -> None:
        if self.loaded:
            return
        data = await fetch_json(
            client,
            "GET",
            COMPANY_TICKERS_URL,
            rate_limiter,
            headers,
            max_retries=retries,
            timeout=timeout,
        )
        if not data:
            logger.warning("Failed to load company_tickers.json; ticker resolution may be limited.")
            self.loaded = True
            return
        for _, record in data.items():
            cik_str = str(record.get("cik_str", "")).zfill(10)
            ticker = str(record.get("ticker", "")).upper()
            title = str(record.get("title", ""))
            if not ticker:
                continue
            t = TickerRecord(cik_str=cik_str, ticker=ticker, title=title)
            self.by_ticker[ticker] = t
            self.by_cik.setdefault(cik_str, []).append(t)
        self.loaded = True


class EdgarScraper:
    def __init__(
        self,
        client: httpx.AsyncClient,
        rate_limiter: RateLimiter,
        config: ScraperInput,
        user_agent: str | None = None,
    ) -> None:
        self.client = client
        self.rate_limiter = rate_limiter
        self.config = config
        self.headers = build_headers(user_agent)
        self.tickers = TickerCache()
        self.timeout = float(config.timeout_secs)
        self.retries = int(config.max_retries)

    async def scrape(self) -> AsyncGenerator[dict[str, Any], None]:
        if self.config.mode.value == "resolve_entity":
            async for item in self._resolve_entity():
                yield item
        elif self.config.mode.value == "search_filings":
            async for item in self._search_filings():
                yield item
        else:
            async for item in self._get_company_facts():
                yield item

    async def _resolve_to_cik(self) -> tuple[str | None, str | None]:
        # Attempt order: explicit CIK > ticker symbol > ticker cache name search > EFTS search
        if self.config.cik:
            return self.config.cik, None

        # Always load ticker cache for resolution
        await self.tickers.ensure(
            self.client, self.headers, self.rate_limiter, self.timeout, self.retries
        )

        # Try explicit ticker symbol
        if self.config.ticker:
            rec = self.tickers.by_ticker.get(self.config.ticker)
            if rec:
                return rec.cik_str, rec.title

        # Try matching query as ticker symbol first
        if self.config.query:
            query_upper = self.config.query.strip().upper()
            rec = self.tickers.by_ticker.get(query_upper)
            if rec:
                return rec.cik_str, rec.title

            # Try matching query against company names in ticker cache
            query_lower = self.config.query.strip().lower()
            for ticker_rec in self.tickers.by_ticker.values():
                if query_lower in ticker_rec.title.lower():
                    return ticker_rec.cik_str, ticker_rec.title

        # Fall back to EFTS full-text search (GET with query params)
        if self.config.query:
            params: dict[str, Any] = {
                "q": self.config.query,
                "from": 0,
                "size": 1,
            }
            data = await fetch_json(
                self.client,
                "GET",
                EFTS_SEARCH_URL,
                self.rate_limiter,
                self.headers,
                max_retries=self.retries,
                timeout=self.timeout,
                params=params,
            )
            hits = data.get("hits", {}) if data else {}
            total = hits.get("total", {})
            total_val = total.get("value", 0) if isinstance(total, dict) else total
            if total_val > 0:
                hit = hits.get("hits", [{}])[0].get("_source", {})
                ciks = hit.get("ciks", [])
                display_names = hit.get("display_names", [])
                cik_val = str(ciks[0]).zfill(10) if ciks else None
                name = None
                if display_names:
                    name = display_names[0].split("  (")[0].strip()
                return cik_val, name

        return None, None

    async def _resolve_entity(self) -> AsyncGenerator[dict[str, Any], None]:
        cik, name_override = await self._resolve_to_cik()
        if not cik:
            logger.warning("No matching CIK found for provided input")
            return

        sub_url = SUBMISSIONS_URL.format(cik=cik)
        submissions = await fetch_json(
            self.client,
            "GET",
            sub_url,
            self.rate_limiter,
            self.headers,
            max_retries=self.retries,
            timeout=self.timeout,
        )
        if not submissions:
            logger.warning(f"No submissions found for CIK {cik}")
            return

        company = submissions.get("companyName", name_override or "")
        tickers = submissions.get("tickers", [])
        sic = submissions.get("sic", "") or ""
        sic_desc = submissions.get("sicDescription", "") or ""
        state = submissions.get("stateOfIncorporation", "") or ""
        country = submissions.get("stateOfIncorporationCountry", "") or ""
        fiscal_year_end = submissions.get("fiscalYearEnd", "") or ""
        mailing = submissions.get("mailingAddress") or {}
        business = submissions.get("businessAddress") or {}
        former_names = [fn.get("name", "") for fn in submissions.get("formerNames", [])]

        recent_filings: list[dict[str, Any]] = []
        recent = submissions.get("recent", {})
        if recent:
            max_filings = max(1, min(self.config.max_recent_filings, 100))
            forms = recent.get("form", [])
            filings_cik = recent.get("cik", [])
            filings_acc = recent.get("accessionNumber", [])
            filings_primary = recent.get("primaryDocument", [])
            filings_dates = recent.get("filingDate", [])
            for form, acc, primary, fdate, cik_val in zip(
                forms, filings_acc, filings_primary, filings_dates, filings_cik
            ):
                if len(recent_filings) >= max_filings:
                    break
                if not self.config.include_amendments and isinstance(form, str) and form.endswith("/A"):
                    continue
                if self.config.form_prefix and isinstance(form, str):
                    if not form.upper().startswith(self.config.form_prefix.upper()):
                        continue
                filing_url = build_filing_url(acc)
                primary_url = build_primary_doc_url(acc, primary)
                recent_filings.append(
                    {
                        "form": form,
                        "fileDate": fdate,
                        "accessionNumber": acc,
                        "filingUrl": filing_url,
                        "primaryDocumentUrl": primary_url,
                        "cik": str(cik_val).zfill(10),
                    }
                )

        entity = EntityProfile(
            cik=cik,
            name=company,
            tickers=tickers,
            sic=sic,
            sic_description=sic_desc,
            state=state,
            country=country,
            fiscal_year_end=fiscal_year_end,
            mailing_address=mailing,
            business_address=business,
            former_names=[fn for fn in former_names if fn],
            recent_filings=recent_filings,
            source_urls=[sub_url],
        )
        yield entity.model_dump()

    async def _search_filings(self) -> AsyncGenerator[dict[str, Any], None]:
        # Resolve target CIK if needed
        cik, name_override = await self._resolve_to_cik()
        query = self.config.query
        if cik and not query:
            query = cik

        params: dict[str, Any] = {
            "q": query or "",
            "from": self.config.start,
            "size": min(self.config.max_results, 50),
        }
        if self.config.form_types:
            params["forms"] = ",".join(self.config.form_types)
        if self.config.date_from:
            params["startdt"] = self.config.date_from
        if self.config.date_to:
            params["enddt"] = self.config.date_to
        if self.config.date_from or self.config.date_to:
            params["dateRange"] = "custom"

        data = await fetch_json(
            self.client,
            "GET",
            EFTS_SEARCH_URL,
            self.rate_limiter,
            self.headers,
            max_retries=self.retries,
            timeout=self.timeout,
            params=params,
        )
        if not data:
            return

        hits = data.get("hits", {})
        items = hits.get("hits", [])
        total_raw = hits.get("total", 0)
        total = total_raw.get("value", 0) if isinstance(total_raw, dict) else total_raw
        if not items:
            return

        for hit in items:
            src = hit.get("_source", {})
            form = src.get("form", "")
            if not self.config.include_amendments and isinstance(form, str) and form.endswith("/A"):
                continue
            if self.config.form_prefix and isinstance(form, str):
                if not form.upper().startswith(self.config.form_prefix.upper()):
                    continue
            accession = src.get("adsh", "")
            primary_doc = src.get("primary_document", "")
            cik_list = src.get("ciks", [])
            cik_val = str(cik_list[0]).zfill(10) if cik_list else ""
            display_names = src.get("display_names", [])
            name = name_override or (display_names[0].split("  (")[0].strip() if display_names else "")
            filing = FilingRecord(
                cik=cik_val,
                name=name,
                tickers=src.get("tickers", []),
                form=form,
                file_date=src.get("file_date", "") or "",
                acceptance_datetime=src.get("filed_at", "") or "",
                accession_number=accession,
                filing_url=build_filing_url(accession) if accession else "",
                primary_document_url=build_primary_doc_url(accession, primary_doc)
                if accession and primary_doc
                else "",
                items=src.get("items", []) or [],
                state=src.get("state", "") or "",
                sic=src.get("sic", "") or "",
                sic_description=src.get("sic_description", "") or "",
            )
            yield filing.model_dump()

        # If pagination needed, EFTS supports start/count; basic single-page for now
        if total > len(items):
            logger.info(
                f"Results truncated: returned {len(items)} of {total}. Increase start/count for pagination."
            )

    async def _get_company_facts(self) -> AsyncGenerator[dict[str, Any], None]:
        cik, name_override = await self._resolve_to_cik()
        if not cik:
            logger.warning("No matching CIK found for facts")
            return

        facts_url = COMPANY_FACTS_URL.format(cik=cik)
        data = await fetch_json(
            self.client,
            "GET",
            facts_url,
            self.rate_limiter,
            self.headers,
            max_retries=self.retries,
            timeout=self.timeout,
        )
        if not data:
            return

        company = data.get("entityName", name_override or "")
        sic = data.get("sic", "") or ""
        facts = data.get("facts", {}) or {}

        namespaces = {ns.lower() for ns in self.config.namespaces} if self.config.namespaces else None
        concepts_filter = {c.lower() for c in self.config.concepts} if self.config.concepts else None
        period_type = self.config.period_type.lower() if self.config.period_type else None

        for ns_name, ns_body in facts.items():
            if namespaces and ns_name.lower() not in namespaces:
                continue
            for concept, concept_body in ns_body.items():
                if concepts_filter and concept.lower() not in concepts_filter:
                    continue
                units = concept_body.get("units", {}) or {}
                for unit_name, unit_values in units.items():
                    for entry in unit_values:
                        start = entry.get("start")
                        end = entry.get("end")
                        if period_type == "instant" and start:
                            continue
                        if period_type == "duration" and not start:
                            continue
                        filing_url = ""
                        if accession := entry.get("accn"):
                            filing_url = build_filing_url(accession)
                        record = FactRecord(
                            cik=cik,
                            name=company,
                            sic=sic,
                            concept=concept,
                            namespace=ns_name,
                            label=concept_body.get("label", "") or "",
                            unit=unit_name,
                            value=entry.get("val"),
                            start=start or "",
                            end=end or "",
                            form=entry.get("form", "") or "",
                            frame=entry.get("frame", "") or "",
                            filing_url=filing_url,
                        )
                        yield record.model_dump()
