import asyncio
from typing import List, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.plugins.logging_plugin import LoggingPlugin
from google.genai import types

from src.agents.processing_pipeline import create_processing_pipeline
from src.tools.dedup import deduplicate_articles_tool
from src.tools.storage import store_articles
from src.tools.fetch_rss import fetch_all_rss
from src.utils.json_utils import parse_pydantic_safe
from src.models.article import Article, FilterResult, TagResult
from src.utils.logger import get_logger

logger = get_logger(__name__)

load_dotenv()


@dataclass
class PipelineConfig:
    """Configuration for the Hybrid Tool Pipeline."""
    model_name: str = "gemini-2.5-flash-lite"
    max_articles: int = -1
    concurrency_limit: int = 3
    retry_attempts: int = 5
    retry_delay_multiplier: int = 7
    retry_initial_delay: int = 1
    user_id: str = "pipeline_user"
    app_name: str = "hybrid_tool_pipeline"


class HybridToolPipeline:
    """
    Hybrid AI News Pipeline using:
        - FunctionTools for fetch + dedup + storage
        - SequentialAgent for LLM-based filtering and tagging
        - Orchestrator agent coordinating all tool calls
    """

    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.session_service = InMemorySessionService()

        self.retry_options = types.HttpRetryOptions(
            attempts=self.config.retry_attempts,
            exp_base=self.config.retry_delay_multiplier,
            initial_delay=self.config.retry_initial_delay,
            http_status_codes=[429, 500, 503, 504],
        )
        
        self.llm_pipeline = create_processing_pipeline(
            model_name=self.config.model_name, retry_config=self.retry_options
        )
        
        self.llm_runner = Runner(
            app_name=self.config.app_name,
            agent=self.llm_pipeline,
            session_service=self.session_service,
            plugins=[LoggingPlugin()]
        )

    # -------------------------------------------------------------------------
    # Phase 1 — Fetch & Dedup (PER FEED)
    # -------------------------------------------------------------------------

    async def _phase_fetch_dedup(self, feed_urls: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch articles from all feeds, deduplicate each feed independently,
        and return a combined list of per-feed unique articles.
        """
        logger.info("=== Phase 1: Fetch & Dedup (per-feed processing) ===")
        

        feed_fetch_results = fetch_all_rss(feed_urls)

        if not feed_fetch_results:
            logger.warning("No feed data returned from fetch.")
            return []

        # Step 2: Dedup per feed
        all_unique_articles = []

        for feed in feed_fetch_results:
            feed_url = feed.feed_url
            last_build_date = feed.last_build_date
            articles = feed.articles
            
            logger.info(f"Deduplicating feed: {feed_url}")
            logger.info(f"Fetched {len(articles)} raw items")

            dedup_result = deduplicate_articles_tool(
                feed_url=feed_url,
                articles=articles,
                feed_last_build_date=last_build_date
            )
            
            if dedup_result:
                unique = dedup_result.articles
                logger.info(f"Unique articles from {feed_url}: {len(unique)}")
                all_unique_articles.extend(unique)  

        return all_unique_articles

    # -------------------------------------------------------------------------
    # Phase 2 — Filter + Tag per article
    # -------------------------------------------------------------------------

    async def _process_single_article(self, article: Article, index: int, total: int, semaphore: asyncio.Semaphore):
        """Run LLM pipeline for a single article."""
        async with semaphore:
            title = article.title
            title_short = title[:50] + "..." if len(title) > 50 else title
            logger.debug(f"[{index}/{total}] Processing: {title_short}")

            session_id = f"article_{index}"
            await self.session_service.create_session(
                app_name=self.config.app_name,
                user_id=self.config.user_id,
                session_id=session_id
            )

            article_prompt = f"""
            Title: {title}
            Summary: {article.summary}
            Link: {article.link}
            """

            filter_result = None
            tag_result = None

            async for event in self.llm_runner.run_async(
                user_id=self.config.user_id,
                session_id=session_id,
                new_message=types.Content(parts=[types.Part.from_text(text=article_prompt)])
            ):
                if event.author == "filter_agent" and event.content:
                    filter_result = event.content.parts[0].text
                elif event.author == "tagging_agent" and event.content:
                    tag_result = event.content.parts[0].text

            if filter_result:
                filter_data = parse_pydantic_safe(filter_result, FilterResult)
                if filter_data and filter_data.is_ai:
                    logger.info(f"✓ AI-related: {title}")
                    if tag_result:
                        tag_data = parse_pydantic_safe(tag_result, TagResult)
                        article.tags = tag_data.tags if tag_data else []
                    else:
                        article.tags = []
                    return article
                else:
                    reason = filter_data.reasoning if filter_data else "Unknown"
                    logger.info(f"✗ Not AI-related: {title} - {reason}")

            return None

    async def _phase_process_articles(self, articles: List[Article]):
        """Run AI filter + tag pipeline on articles."""
        logger.info("=== Phase 2: Filter & Tag ===")

        if self.config.max_articles == -1:
            logger.info("Processing all articles.")
        elif len(articles) > self.config.max_articles:
            logger.info(f"Limiting to first {self.config.max_articles} articles.")
            articles = articles[:self.config.max_articles]

        logger.info(f"Processing {len(articles)} articles (concurrency={self.config.concurrency_limit})...")

        semaphore = asyncio.Semaphore(self.config.concurrency_limit)
        tasks = [
            self._process_single_article(article, i, len(articles), semaphore)
            for i, article in enumerate(articles, 1)
        ]

        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

    # -------------------------------------------------------------------------
    # Phase 3 — Store filtered articles
    # -------------------------------------------------------------------------

    async def _phase_storage(self, articles: List[Article]):
        if not articles:
            logger.info("No articles to store.")
            return

        logger.info(f"Storing {len(articles)} articles...")
        store_articles(articles)

    # -------------------------------------------------------------------------
    # Run Pipeline
    # -------------------------------------------------------------------------

    async def run_async(self, feed_urls: List[str]):
        logger.info("Starting Hybrid Tool Pipeline...")
        logger.info(f"Processing {len(feed_urls)} RSS feeds...")

        # Phase 1 – Fetch + Dedup per feed
        unique_articles = await self._phase_fetch_dedup(feed_urls)

        if not unique_articles:
            logger.warning("No unique articles available. Stopping.")
            return

        # Phase 2 – LLM filtering + tagging
        ai_articles = await self._phase_process_articles(unique_articles)

        # Phase 3 – Storage
        await self._phase_storage(ai_articles)

        logger.info("✅ Pipeline Complete!")
        logger.info(f"Unique fetched articles: {len(unique_articles)}")
        logger.info(f"AI-related articles stored: {len(ai_articles)}")

    def run(self, feed_urls: List[str]):
        return asyncio.run(self.run_async(feed_urls))


if __name__ == "__main__":
    pipeline = HybridToolPipeline()
    feeds = ["https://www.databricks.com/feed"]
    pipeline.run(feeds)
