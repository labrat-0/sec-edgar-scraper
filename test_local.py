import asyncio
import json
from pathlib import Path

import httpx

from src.models import ScraperInput
from src.scraper import EdgarScraper
from src.utils import RateLimiter


async def run_once(payload: dict):
    config = ScraperInput.from_actor_input(payload)
    async with httpx.AsyncClient() as client:
        scraper = EdgarScraper(client, RateLimiter(), config)
        items = []
        async for item in scraper.scrape():
            items.append(item)
            if len(items) >= 3:
                break
        return items


def test_resolve_entity_smoke():
    payload = {"mode": "resolve_entity", "query": "NVIDIA", "maxRecentFilings": 3}
    items = asyncio.run(run_once(payload))
    assert items, "Expected at least one entity result"
    assert items[0]["type"] == "entity"


def test_search_filings_smoke():
    payload = {"mode": "search_filings", "query": "NVIDIA", "maxResults": 5}
    items = asyncio.run(run_once(payload))
    assert items, "Expected filings results"
    assert items[0]["type"] == "filing"


def test_company_facts_smoke():
    payload = {"mode": "get_company_facts", "query": "NVIDIA"}
    items = asyncio.run(run_once(payload))
    # May be empty if resolution fails, but ensure no crash
    assert isinstance(items, list)


if __name__ == "__main__":
    data = asyncio.run(run_once({"mode": "resolve_entity", "query": "NVIDIA"}))
    Path("sample.json").write_text(json.dumps(data, indent=2))
    print("Wrote sample.json")
