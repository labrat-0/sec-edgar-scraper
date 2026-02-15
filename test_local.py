"""Local test script -- tests all 3 scraping modes against live APIs.

Run: .venv/bin/python test_local.py

No API key required. All data sources are public.
This bypasses the Apify Actor wrapper and tests the core scraping logic directly.
"""

import asyncio
import json
import sys
import time

import httpx

# Add src to path so we can import directly
sys.path.insert(0, ".")

from src.models import ScraperInput, ScrapingMode
from src.scraper import AiMlScraper
from src.utils import RateLimiter


async def test_mode(name: str, config: ScraperInput, max_items: int = 5) -> bool:
    """Test a single scraping mode. Returns True on success."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")

    rate_limiter = RateLimiter(interval=0.5)

    async with httpx.AsyncClient() as client:
        scraper = AiMlScraper(client, rate_limiter, config)

        items = []
        try:
            async for item in scraper.scrape():
                items.append(item)
                if len(items) >= max_items:
                    break
        except Exception as e:
            print(f"  FAIL: {e}")
            import traceback
            traceback.print_exc()
            return False

    if not items:
        print(f"  FAIL: No items returned")
        return False

    print(f"  OK: Got {len(items)} items")
    # Print first item as sample
    print(f"  Sample item:")
    sample = json.dumps(items[0], indent=2, default=str)
    # Truncate long output
    if len(sample) > 800:
        sample = sample[:800] + "\n  ..."
    print(f"  {sample}")

    return True


async def main():
    results = {}
    start = time.time()

    # Test 1: Search Models (HuggingFace Hub)
    config = ScraperInput(
        mode=ScrapingMode.SEARCH_MODELS,
        query="large language model",
        sort="downloads",
        max_results=5,
    )
    results["search_models"] = await test_mode(
        "Search Models ('large language model', sorted by downloads)", config, max_items=5
    )

    # Test 2: Search Models with pipeline tag filter
    config = ScraperInput(
        mode=ScrapingMode.SEARCH_MODELS,
        query="stable diffusion",
        pipeline_tag="text-to-image",
        sort="likes",
        max_results=5,
    )
    results["search_models_filtered"] = await test_mode(
        "Search Models ('stable diffusion', text-to-image, sorted by likes)", config, max_items=5
    )

    # Test 3: Search Papers (arXiv)
    config = ScraperInput(
        mode=ScrapingMode.SEARCH_PAPERS,
        query="transformer",
        arxiv_category="cs.CL",
        sort="submittedDate",
        max_results=5,
    )
    results["search_papers"] = await test_mode(
        "Search Papers ('transformer', cs.CL category)", config, max_items=5
    )

    # Test 4: Search Papers by author
    config = ScraperInput(
        mode=ScrapingMode.SEARCH_PAPERS,
        author="Yann LeCun",
        sort="submittedDate",
        max_results=5,
    )
    results["search_papers_author"] = await test_mode(
        "Search Papers (author: 'Yann LeCun')", config, max_items=5
    )

    # Test 5: Trending Papers (HuggingFace Daily Papers)
    config = ScraperInput(
        mode=ScrapingMode.TRENDING_PAPERS,
        max_results=5,
    )
    results["trending_papers"] = await test_mode(
        "Trending Papers (daily feed, no filter)", config, max_items=5
    )

    # Test 6: Trending Papers with keyword filter
    config = ScraperInput(
        mode=ScrapingMode.TRENDING_PAPERS,
        query="language",
        max_results=5,
    )
    results["trending_papers_filtered"] = await test_mode(
        "Trending Papers (keyword: 'language')", config, max_items=5
    )

    # Summary
    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"RESULTS ({elapsed:.1f}s)")
    print(f"{'='*60}")
    all_passed = True
    for mode, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {mode}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print(f"\nAll tests passed.")
    else:
        print(f"\nSome tests FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
