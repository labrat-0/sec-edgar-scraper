from __future__ import annotations

import logging
import os

import httpx
from apify import Actor

from .models import ScraperInput
from .scraper import EdgarScraper
from .utils import RateLimiter

logger = logging.getLogger(__name__)

FREE_TIER_LIMIT = 25


async def main() -> None:
    async with Actor:
        raw_input = await Actor.get_input() or {}
        config = ScraperInput.from_actor_input(raw_input)

        validation_error = config.validate_for_mode()
        if validation_error:
            await Actor.fail(status_message=validation_error)
            return

        is_paying = os.environ.get("APIFY_IS_AT_HOME") == "1" and os.environ.get(
            "APIFY_USER_IS_PAYING"
        ) == "1"

        max_results = config.max_results
        if not is_paying and os.environ.get("APIFY_IS_AT_HOME") == "1":
            max_results = min(max_results, FREE_TIER_LIMIT)
            Actor.log.info(
                f"Free tier: limited to {FREE_TIER_LIMIT} results. "
                "Subscribe to the actor for unlimited results."
            )

        Actor.log.info(
            "Starting SEC EDGAR Entity Resolver | mode=%s | max_results=%s",
            config.mode.value,
            max_results,
        )

        state = await Actor.use_state(default_value={"scraped": 0, "failed": 0})

        await Actor.set_status_message("Connecting to SEC EDGAR...")

        headers_ua = raw_input.get("userAgent") or raw_input.get("user_agent")

        async with httpx.AsyncClient() as client:
            rate_limiter = RateLimiter(interval=config.request_interval_secs)
            scraper = EdgarScraper(client, rate_limiter, config, user_agent=headers_ua)

            count = state["scraped"]
            batch: list[dict] = []
            batch_size = 25

            try:
                async for item in scraper.scrape():
                    if count >= max_results:
                        break

                    batch.append(item)
                    count += 1
                    state["scraped"] = count

                    if len(batch) >= batch_size:
                        await Actor.push_data(batch)
                        batch = []
                        await Actor.set_status_message(f"Scraped {count}/{max_results} items")

                if batch:
                    await Actor.push_data(batch)

            except Exception as e:  # pragma: no cover - defensive
                state["failed"] += 1
                Actor.log.error(f"Scraping error: {e}")
                if batch:
                    await Actor.push_data(batch)

        msg = f"Done. Scraped {count} items."
        if state["failed"] > 0:
            msg += f" {state['failed']} errors encountered."
        if (
            not is_paying
            and os.environ.get("APIFY_IS_AT_HOME") == "1"
            and count >= FREE_TIER_LIMIT
        ):
            msg += (
                f" Free tier limit ({FREE_TIER_LIMIT}) reached." " Subscribe for unlimited results."
            )

        Actor.log.info(msg)
        await Actor.set_status_message(msg)
