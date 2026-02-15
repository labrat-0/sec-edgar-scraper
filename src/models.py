from __future__ import annotations

from enum import Enum
from typing import Any, Iterable

from pydantic import BaseModel, Field, field_validator


class ScrapingMode(str, Enum):
    RESOLVE_ENTITY = "resolve_entity"
    SEARCH_FILINGS = "search_filings"
    GET_COMPANY_FACTS = "get_company_facts"


class ScraperInput(BaseModel):
    mode: ScrapingMode = ScrapingMode.RESOLVE_ENTITY
    query: str = ""
    cik: str = ""
    ticker: str = ""
    form_types: list[str] = Field(default_factory=list)
    date_from: str = ""
    date_to: str = ""
    max_results: int = 100
    start: int = 0
    max_recent_filings: int = 10
    namespaces: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    period_type: str = ""
    include_amendments: bool = True
    form_prefix: str = ""
    request_interval_secs: float = 0.3
    timeout_secs: int = 30
    max_retries: int = 5

    @field_validator("cik")
    @classmethod
    def normalize_cik(cls, v: str) -> str:
        v = v.strip()
        if not v:
            return ""
        digits = "".join(ch for ch in v if ch.isdigit())
        if not digits:
            raise ValueError("CIK must contain digits")
        if len(digits) > 10:
            raise ValueError("CIK must be at most 10 digits")
        return digits.zfill(10)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("form_prefix")
    @classmethod
    def normalize_form_prefix(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("form_types", mode="before")
    @classmethod
    def normalize_form_types(cls, v: Iterable[str] | Any) -> list[str]:
        if not v:
            return []
        if isinstance(v, str):
            return [v.strip().upper()] if v.strip() else []
        return [str(item).strip().upper() for item in v if str(item).strip()]

    @classmethod
    def from_actor_input(cls, raw: dict[str, Any]) -> ScraperInput:
        return cls(
            mode=raw.get("mode", ScrapingMode.RESOLVE_ENTITY),
            query=raw.get("query", ""),
            cik=raw.get("cik", ""),
            ticker=raw.get("ticker", ""),
            form_types=raw.get("formTypes", []) or raw.get("form_types", []),
            date_from=raw.get("dateFrom", ""),
            date_to=raw.get("dateTo", ""),
            max_results=raw.get("maxResults", 100),
            start=raw.get("start", 0),
            max_recent_filings=raw.get("maxRecentFilings", 10),
            namespaces=raw.get("namespaces", []),
            concepts=raw.get("concepts", []),
            period_type=raw.get("periodType", ""),
            include_amendments=raw.get("includeAmendments", True),
            form_prefix=raw.get("formPrefix", ""),
            request_interval_secs=raw.get("requestIntervalSecs", 0.3),
            timeout_secs=raw.get("timeoutSecs", 30),
            max_retries=raw.get("maxRetries", 5),
        )

    def validate_for_mode(self) -> str | None:
        if self.mode == ScrapingMode.RESOLVE_ENTITY:
            if not (self.query or self.cik or self.ticker):
                return "Provide at least one of: query (company name), ticker, or CIK for resolve_entity."
        if self.mode == ScrapingMode.SEARCH_FILINGS:
            if not (self.query or self.cik or self.ticker or self.form_types):
                return "Provide a query, CIK/ticker, or formTypes for search_filings."
        if self.mode == ScrapingMode.GET_COMPANY_FACTS:
            if not (self.cik or self.ticker):
                return "Provide CIK or ticker for get_company_facts."
        return None


class TickerRecord(BaseModel):
    cik_str: str
    ticker: str
    title: str


class EntityProfile(BaseModel):
    schema_version: str = "1.0"
    type: str = "entity"
    cik: str
    name: str
    tickers: list[str] = Field(default_factory=list)
    sic: str = ""
    sic_description: str = ""
    state: str = ""
    country: str = ""
    fiscal_year_end: str = ""
    mailing_address: dict[str, str] = Field(default_factory=dict)
    business_address: dict[str, str] = Field(default_factory=dict)
    former_names: list[str] = Field(default_factory=list)
    recent_filings: list[dict[str, Any]] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


class FilingRecord(BaseModel):
    schema_version: str = "1.0"
    type: str = "filing"
    cik: str
    name: str = ""
    tickers: list[str] = Field(default_factory=list)
    form: str = ""
    file_date: str = ""
    acceptance_datetime: str = ""
    accession_number: str = ""
    filing_url: str = ""
    primary_document_url: str = ""
    items: list[str] = Field(default_factory=list)
    state: str = ""
    sic: str = ""
    sic_description: str = ""


class FactRecord(BaseModel):
    schema_version: str = "1.0"
    type: str = "fact"
    cik: str
    name: str = ""
    sic: str = ""
    concept: str = ""
    namespace: str = ""
    label: str = ""
    unit: str = ""
    value: float | int | str | None = None
    start: str = ""
    end: str = ""
    form: str = ""
    frame: str = ""
    filing_url: str = ""
