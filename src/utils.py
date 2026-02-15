"""Utility functions for rate limiting, retries, and HTTP helpers."""

from __future__ import annotations

import asyncio
import logging
import xml.etree.ElementTree as ET
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Public APIs -- be polite but no strict rate limits
REQUEST_INTERVAL = 0.5  # seconds between requests

# Retry settings
MAX_RETRIES = 3
RETRY_BASE_DELAY = 3.0  # seconds

# API base URLs
HUGGINGFACE_MODELS_URL = "https://huggingface.co/api/models"
HUGGINGFACE_DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"
ARXIV_API_URL = "https://export.arxiv.org/api/query"


class RateLimiter:
    """Simple rate limiter that ensures a minimum interval between requests."""

    def __init__(self, interval: float = REQUEST_INTERVAL) -> None:
        self._interval = interval
        self._last_request: float = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        """Wait until it's safe to make another request."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request
            if elapsed < self._interval:
                wait_time = self._interval - elapsed
                logger.debug(f"Rate limiter: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
            self._last_request = asyncio.get_event_loop().time()


async def fetch_json(
    client: httpx.AsyncClient,
    url: str,
    rate_limiter: RateLimiter,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any] | None:
    """Fetch JSON from a URL with rate limiting and retry logic.

    Returns the parsed JSON data, or None if all retries fail.
    """
    for attempt in range(MAX_RETRIES):
        await rate_limiter.wait()

        try:
            response = await client.get(
                url,
                params=params,
                timeout=30.0,
                follow_redirects=True,
            )

            if response.status_code == 200:
                return response.json()

            if response.status_code == 429:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    f"Rate limited (429) on {url}. "
                    f"Retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})"
                )
                await asyncio.sleep(delay)
                continue

            if response.status_code == 403:
                logger.error(f"Forbidden (403) on {url}.")
                return None

            if response.status_code == 400:
                logger.error(
                    f"Bad request (400) on {url}. "
                    f"Response: {response.text[:500]}"
                )
                return None

            if response.status_code == 404:
                logger.warning(f"Not found (404): {url}")
                return None

            if response.status_code >= 500:
                delay = 10.0 * (attempt + 1)
                logger.warning(
                    f"Server error ({response.status_code}) on {url}. "
                    f"Retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})"
                )
                await asyncio.sleep(delay)
                continue

            logger.warning(
                f"Unexpected status {response.status_code} on {url}. "
                f"Response: {response.text[:300]}"
            )
            return None

        except httpx.TimeoutException:
            delay = 10.0 * (attempt + 1)
            logger.warning(
                f"Timeout on {url}. "
                f"Retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})"
            )
            await asyncio.sleep(delay)
            continue

        except httpx.HTTPError as e:
            delay = 10.0 * (attempt + 1)
            logger.warning(
                f"HTTP error on {url}: {e}. "
                f"Retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})"
            )
            await asyncio.sleep(delay)
            continue

    logger.error(f"All {MAX_RETRIES} retries exhausted for {url}")
    return None


async def fetch_xml(
    client: httpx.AsyncClient,
    url: str,
    rate_limiter: RateLimiter,
    params: dict[str, Any] | None = None,
) -> ET.Element | None:
    """Fetch XML from a URL with rate limiting and retry logic.

    Returns the parsed XML root element, or None if all retries fail.
    Used for arXiv API which returns Atom XML.
    """
    for attempt in range(MAX_RETRIES):
        await rate_limiter.wait()

        try:
            response = await client.get(
                url,
                params=params,
                timeout=30.0,
                follow_redirects=True,
            )

            if response.status_code == 200:
                return ET.fromstring(response.text)

            if response.status_code == 429:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    f"Rate limited (429) on {url}. "
                    f"Retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})"
                )
                await asyncio.sleep(delay)
                continue

            if response.status_code >= 500:
                delay = 10.0 * (attempt + 1)
                logger.warning(
                    f"Server error ({response.status_code}) on {url}. "
                    f"Retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})"
                )
                await asyncio.sleep(delay)
                continue

            logger.warning(
                f"Unexpected status {response.status_code} on {url}. "
                f"Response: {response.text[:300]}"
            )
            return None

        except httpx.TimeoutException:
            delay = 10.0 * (attempt + 1)
            logger.warning(
                f"Timeout on {url}. "
                f"Retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})"
            )
            await asyncio.sleep(delay)
            continue

        except httpx.HTTPError as e:
            delay = 10.0 * (attempt + 1)
            logger.warning(
                f"HTTP error on {url}: {e}. "
                f"Retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})"
            )
            await asyncio.sleep(delay)
            continue

        except ET.ParseError as e:
            logger.error(f"XML parse error on {url}: {e}")
            return None

    logger.error(f"All {MAX_RETRIES} retries exhausted for {url}")
    return None
