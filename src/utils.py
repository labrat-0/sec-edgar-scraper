from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# SEC requirements (override with userAgent input)
DEFAULT_USER_AGENT = "ApifySECResolver (user@example.com)"  # replace at runtime if provided
DEFAULT_REQUEST_INTERVAL = 0.3
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 5

EFTS_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


class RateLimiter:
    """Simple rate limiter that enforces a minimum interval between requests."""

    def __init__(self, interval: float = DEFAULT_REQUEST_INTERVAL) -> None:
        self._interval = interval
        self._last_request: float = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request
            if elapsed < self._interval:
                await asyncio.sleep(self._interval - elapsed)
            self._last_request = asyncio.get_event_loop().time()


def build_headers(user_agent: str | None = None) -> dict[str, str]:
    ua = user_agent.strip() if user_agent else DEFAULT_USER_AGENT
    return {
        "User-Agent": ua,
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
    }


async def fetch_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    rate_limiter: RateLimiter,
    headers: dict[str, str],
    max_retries: int = DEFAULT_MAX_RETRIES,
    timeout: float = DEFAULT_TIMEOUT,
    json: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any] | None:
    """HTTP JSON fetch with retries/backoff and SEC headers."""
    for attempt in range(max_retries + 1):
        await rate_limiter.wait()
        try:
            response = await client.request(
                method,
                url,
                headers=headers,
                json=json,
                params=params,
                timeout=timeout,
            )

            status = response.status_code
            if status == 200:
                return response.json()

            if status in {429, 503, 502, 500}:
                delay = min(15.0, 1.5 * (2**attempt))
                jitter = random.uniform(0, 0.5)
                total = delay + jitter
                logger.warning(
                    f"{status} on {url} attempt {attempt+1}/{max_retries}. "
                    f"Retrying in {total:.1f}s"
                )
                await asyncio.sleep(total)
                continue

            if status == 403:
                logger.error("403 Forbidden - check SEC User-Agent and etiquette.")
                return None

            if status == 404:
                logger.info(f"404 Not Found: {url}")
                return None

            logger.warning(
                f"Unexpected status {status} on {url}. Body: {response.text[:300]}"
            )
            return None

        except httpx.TimeoutException:
            delay = min(20.0, 2.0 * (attempt + 1))
            logger.warning(
                f"Timeout on {url} attempt {attempt+1}/{max_retries}. "
                f"Retrying in {delay:.1f}s"
            )
            await asyncio.sleep(delay)
            continue
        except httpx.HTTPError as e:
            delay = min(20.0, 2.0 * (attempt + 1))
            logger.warning(
                f"HTTP error on {url}: {e}. attempt {attempt+1}/{max_retries}. "
                f"Retrying in {delay:.1f}s"
            )
            await asyncio.sleep(delay)
            continue

    logger.error(f"All retries exhausted for {url}")
    return None


def build_primary_doc_url(accession: str, primary_doc: str) -> str:
    acc_no_dashes = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(acc_no_dashes):010d}/{acc_no_dashes}/{primary_doc}"


def build_filing_url(accession: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{int(accession.replace('-', '')):010d}/{accession.replace('-', '')}/{accession}-index.htm"
