"""Core scraping logic for AI/ML Intelligence Scraper.

All 3 modes: search_models (HuggingFace), search_papers (arXiv), trending_papers (HuggingFace Daily Papers).
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

import httpx

from .models import (
    ScraperInput,
    ScrapingMode,
    format_arxiv_paper,
    format_hf_paper,
    format_model,
)
from .utils import (
    ARXIV_API_URL,
    HUGGINGFACE_DAILY_PAPERS_URL,
    HUGGINGFACE_MODELS_URL,
    RateLimiter,
    fetch_json,
    fetch_xml,
)

logger = logging.getLogger(__name__)

# HuggingFace API doesn't document a strict max, but 100 per page is safe
HF_PAGE_SIZE = 100

# arXiv API max results per request
ARXIV_PAGE_SIZE = 200


class AiMlScraper:
    """Scrapes AI/ML data from HuggingFace Hub and arXiv APIs."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        rate_limiter: RateLimiter,
        config: ScraperInput,
    ) -> None:
        self.client = client
        self.rate_limiter = rate_limiter
        self.config = config

    async def scrape(self) -> AsyncIterator[dict[str, Any]]:
        """Main entry point -- dispatches to the correct mode."""
        mode = self.config.mode

        if mode == ScrapingMode.SEARCH_MODELS:
            async for item in self._search_models():
                yield item
        elif mode == ScrapingMode.SEARCH_PAPERS:
            async for item in self._search_papers():
                yield item
        elif mode == ScrapingMode.TRENDING_PAPERS:
            async for item in self._trending_papers():
                yield item

    # --- Mode 1: Search Models (HuggingFace) ---

    async def _search_models(self) -> AsyncIterator[dict[str, Any]]:
        """Search HuggingFace Hub models by keyword, task, framework, etc."""
        logger.info(f"Searching HuggingFace models: '{self.config.query}'")

        total_yielded = 0
        consecutive_empty = 0

        # HuggingFace uses cursor-based pagination via the Link header,
        # but also supports simple offset pagination with the `offset` param.
        # We'll use offset for simplicity (same pattern as gov-contracts).
        offset = 0

        while total_yielded < self.config.max_results:
            page_size = min(
                HF_PAGE_SIZE,
                self.config.max_results - total_yielded,
            )

            params = self._build_model_params(page_size, offset)

            data = await fetch_json(
                self.client,
                HUGGINGFACE_MODELS_URL,
                self.rate_limiter,
                params,
            )

            if not data or not isinstance(data, list):
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    logger.info("No more model results from HuggingFace")
                    break
                offset += page_size
                continue

            if len(data) == 0:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    logger.info("No more model results from HuggingFace")
                    break
                offset += page_size
                continue

            consecutive_empty = 0

            for model_data in data:
                yield format_model(model_data)
                total_yielded += 1
                if total_yielded >= self.config.max_results:
                    break

            logger.info(f"Fetched {total_yielded} models so far")

            # If we got fewer results than requested, we've hit the end
            if len(data) < page_size:
                break

            offset += len(data)

    def _build_model_params(
        self, limit: int, offset: int
    ) -> dict[str, Any]:
        """Build query parameters for HuggingFace models API."""
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }

        if self.config.query:
            params["search"] = self.config.query

        # Sort mapping
        sort = self.config.sort
        if sort == "downloads":
            params["sort"] = "downloads"
            params["direction"] = "-1"
        elif sort == "likes":
            params["sort"] = "likes"
            params["direction"] = "-1"
        elif sort == "trending":
            params["sort"] = "trendingScore"
            params["direction"] = "-1"
        else:
            # Default to downloads
            params["sort"] = "downloads"
            params["direction"] = "-1"

        if self.config.pipeline_tag:
            params["pipeline_tag"] = self.config.pipeline_tag

        if self.config.library_filter:
            params["library"] = self.config.library_filter

        return params

    # --- Mode 2: Search Papers (arXiv) ---

    async def _search_papers(self) -> AsyncIterator[dict[str, Any]]:
        """Search arXiv for AI/ML research papers."""
        logger.info(
            f"Searching arXiv papers: query='{self.config.query}' "
            f"category='{self.config.arxiv_category}'"
        )

        total_yielded = 0
        consecutive_empty = 0
        start = 0

        while total_yielded < self.config.max_results:
            page_size = min(
                ARXIV_PAGE_SIZE,
                self.config.max_results - total_yielded,
            )

            search_query = self._build_arxiv_query()

            # Sort mapping
            sort_by = "relevance"
            sort_order = "descending"
            sort = self.config.sort
            if sort == "submittedDate":
                sort_by = "submittedDate"
                sort_order = "descending"
            elif sort == "lastUpdatedDate":
                sort_by = "lastUpdatedDate"
                sort_order = "descending"

            params: dict[str, Any] = {
                "search_query": search_query,
                "start": start,
                "max_results": page_size,
                "sortBy": sort_by,
                "sortOrder": sort_order,
            }

            logger.debug(
                f"arXiv query: search_query='{search_query}' "
                f"start={start} max_results={page_size}"
            )

            root = await fetch_xml(
                self.client,
                ARXIV_API_URL,
                self.rate_limiter,
                params,
            )

            if root is None:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    logger.info("No more results from arXiv")
                    break
                start += page_size
                continue

            # arXiv Atom namespace
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", ns)

            if not entries:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    logger.info("No more results from arXiv")
                    break
                start += page_size
                continue

            consecutive_empty = 0

            for entry in entries:
                paper = format_arxiv_paper(entry)

                # Apply client-side date filtering if specified
                if self.config.date_from or self.config.date_to:
                    pub_date = paper.get("publishedDate", "")
                    if pub_date:
                        # arXiv dates are ISO format: 2026-01-15T12:00:00Z
                        date_str = pub_date[:10]  # YYYY-MM-DD
                        if self.config.date_from and date_str < self.config.date_from:
                            continue
                        if self.config.date_to and date_str > self.config.date_to:
                            continue

                yield paper
                total_yielded += 1
                if total_yielded >= self.config.max_results:
                    break

            logger.info(f"Fetched {total_yielded} papers so far")

            # If we got fewer results than requested, we've hit the end
            if len(entries) < page_size:
                break

            start += len(entries)

            # Safety: arXiv has a practical limit
            if start >= 10000:
                logger.info("Reached maximum arXiv pagination depth (10,000)")
                break

    def _build_arxiv_query(self) -> str:
        """Build the arXiv search query string.

        arXiv query syntax:
        - all:keyword -- search all fields
        - ti:keyword -- search title only
        - abs:keyword -- search abstract only
        - au:name -- search author
        - cat:cs.AI -- search category
        - AND, OR, ANDNOT operators
        """
        parts: list[str] = []

        if self.config.query:
            # Search in all fields (title + abstract)
            query = self.config.query.strip()
            # If query contains spaces, wrap in quotes for exact match
            if " " in query:
                parts.append(f'all:"{query}"')
            else:
                parts.append(f"all:{query}")

        if self.config.arxiv_category:
            parts.append(f"cat:{self.config.arxiv_category}")

        if self.config.author:
            author = self.config.author.strip()
            if " " in author:
                parts.append(f'au:"{author}"')
            else:
                parts.append(f"au:{author}")

        if not parts:
            # Default to all AI/ML categories if nothing specified
            parts.append(
                "cat:cs.AI OR cat:cs.LG OR cat:cs.CL OR cat:cs.CV"
            )

        return " AND ".join(parts) if len(parts) > 1 else parts[0]

    # --- Mode 3: Trending Papers (HuggingFace Daily Papers) ---

    async def _trending_papers(self) -> AsyncIterator[dict[str, Any]]:
        """Fetch trending/daily AI papers from HuggingFace."""
        logger.info("Fetching trending papers from HuggingFace Daily Papers")

        total_yielded = 0
        consecutive_empty = 0
        offset = 0

        while total_yielded < self.config.max_results:
            page_size = min(
                HF_PAGE_SIZE,
                self.config.max_results - total_yielded,
            )

            params: dict[str, Any] = {
                "limit": page_size,
                "offset": offset,
            }

            data = await fetch_json(
                self.client,
                HUGGINGFACE_DAILY_PAPERS_URL,
                self.rate_limiter,
                params,
            )

            if not data or not isinstance(data, list):
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    logger.info("No more trending papers from HuggingFace")
                    break
                offset += page_size
                continue

            if len(data) == 0:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    logger.info("No more trending papers from HuggingFace")
                    break
                offset += page_size
                continue

            consecutive_empty = 0

            for paper_data in data:
                paper = format_hf_paper(paper_data)

                # Optional keyword filtering for trending papers
                if self.config.query:
                    query_lower = self.config.query.lower()
                    title = paper.get("title", "").lower()
                    summary = paper.get("summary", "").lower()
                    if query_lower not in title and query_lower not in summary:
                        continue

                yield paper
                total_yielded += 1
                if total_yielded >= self.config.max_results:
                    break

            logger.info(f"Fetched {total_yielded} trending papers so far")

            # If we got fewer results than requested, we've hit the end
            if len(data) < page_size:
                break

            offset += len(data)
