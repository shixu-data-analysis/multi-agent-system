import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.agents.processing_pipeline import create_processing_pipeline
from src.agents.orchestrator import create_orchestrator

load_dotenv()

@dataclass
class PipelineConfig:
    """Configuration for the Hybrid Tool Pipeline."""
    model_name: str = "gemini-2.5-flash-lite"
    max_articles: int = 6
    concurrency_limit: int = 3  # Limit concurrent LLM calls
    retry_attempts: int = 5
    retry_delay_multiplier: int = 7
    retry_initial_delay: int = 1
    user_id: str = "pipeline_user"
    app_name: str = "hybrid_tool_pipeline"

class HybridToolPipeline:
    """
    Hybrid AI News Pipeline using FunctionTools + SequentialAgent.
    
    Architecture:
    - FunctionTools for utilities (fetch, dedup, storage)
    - SequentialAgent for LLM agents (filter, tag) - processes each article
    - LlmAgent orchestrator coordinates everything
    """
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.session_service = InMemorySessionService()

        # Retry configuration for API calls
        self.retry_options = types.HttpRetryOptions(
            attempts=self.config.retry_attempts,
            exp_base=self.config.retry_delay_multiplier,
            initial_delay=self.config.retry_initial_delay,
            http_status_codes=[429, 500, 503, 504],
        )
        
        # Initialize Agents
        self.llm_pipeline = create_processing_pipeline(
            model_name=self.config.model_name, 
            retry_config=self.retry_options
        )
        self.orchestrator = create_orchestrator(
            model_name=self.config.model_name, 
            retry_config=self.retry_options
        )
        
        # Initialize Runners
        self.llm_runner = Runner(
            app_name=self.config.app_name,
            agent=self.llm_pipeline,
            session_service=self.session_service
        )
        self.orchestrator_runner = Runner(
            app_name=self.config.app_name,
            agent=self.orchestrator,
            session_service=self.session_service
        )

    def _parse_json_safe(self, text: str) -> Optional[Any]:
        """Safely parses JSON from text, handling markdown code blocks."""
        try:
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
        except Exception:
            return None

    async def _phase_fetch_dedup(self, feed_urls: List[str]) -> List[Dict[str, Any]]:
        """Phase 1: Fetch and Deduplicate articles using the Orchestrator."""
        print("=== Phase 1: Fetch & Dedup (using FunctionTools) ===")
        session_id = "orchestrator_session"
        
        await self.session_service.create_session(
            app_name=self.config.app_name,
            user_id=self.config.user_id,
            session_id=session_id
        )
        
        prompt = f"""
        Fetch and deduplicate articles from these RSS feeds: {json.dumps(feed_urls)}
        
        Steps:
        1. Use fetch_rss_articles tool
        2. Use deduplicate_articles tool
        3. Tell me how many unique articles are ready for processing
        """
        
        unique_articles = []
        async for event in self.orchestrator_runner.run_async(
            user_id=self.config.user_id,
            session_id=session_id,
            new_message=types.Content(parts=[types.Part.from_text(text=prompt)])
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        print(f"[Orchestrator]: {part.text}\n")
                    if hasattr(part, 'function_response') and part.function_response:
                        data = part.function_response.response
                        if data and 'articles' in data:
                            unique_articles = data['articles']
        return unique_articles

    async def _process_single_article(self, article: Dict[str, Any], index: int, total: int, semaphore: asyncio.Semaphore) -> Optional[Dict[str, Any]]:
        """Process a single article with concurrency control."""
        async with semaphore:
            title = article.get('title', 'Untitled')
            print(f"[{index}/{total}] Processing: {title[:60]}...")
            
            article_session_id = f"article_{index}"
            await self.session_service.create_session(
                app_name=self.config.app_name,
                user_id=self.config.user_id,
                session_id=article_session_id
            )
            
            article_prompt = f"""
            Title: {title}
            Summary: {article.get('summary')}
            Link: {article.get('link')}
            """
            
            filter_result = None
            tag_result = None
            
            try:
                async for event in self.llm_runner.run_async(
                    user_id=self.config.user_id,
                    session_id=article_session_id,
                    new_message=types.Content(parts=[types.Part.from_text(text=article_prompt)])
                ):
                    if event.author == "filter_agent" and event.content:
                        filter_result = event.content.parts[0].text
                    elif event.author == "tagging_agent" and event.content:
                        tag_result = event.content.parts[0].text
                
                # Process results
                if filter_result:
                    filter_data = self._parse_json_safe(filter_result)
                    if filter_data and filter_data.get("is_ai"):
                        print(f"[{index}] ✓ AI-related")
                        
                        if tag_result:
                            tag_data = self._parse_json_safe(tag_result)
                            article['tags'] = tag_data.get('tags', []) if tag_data else []
                            print(f"[{index}]   Tags: {article['tags']}")
                        else:
                            article['tags'] = []
                            
                        return article
                    else:
                        reason = filter_data.get('reasoning', '') if filter_data else "Unknown"
                        print(f"[{index}] ✗ Not AI-related: {reason}")
            except Exception as e:
                print(f"[{index}] ⚠ Error processing article: {e}")
                
            return None

    async def _phase_process_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Phase 2: Filter and Tag each article using the SequentialAgent concurrently."""
        print(f"\n=== Phase 2: Filter & Tag (using SequentialAgent) ===")
        
        # Apply limit
        if len(articles) > self.config.max_articles:
            print(f"Limiting processing to first {self.config.max_articles} articles (Quota Safety).")
            articles = articles[:self.config.max_articles]
            
        print(f"Processing {len(articles)} articles concurrently (limit={self.config.concurrency_limit})...\n")
        
        semaphore = asyncio.Semaphore(self.config.concurrency_limit)
        tasks = []
        
        for i, article in enumerate(articles, 1):
            task = self._process_single_article(article, i, len(articles), semaphore)
            tasks.append(task)
            
        results = await asyncio.gather(*tasks)
        
        # Filter out None results (non-AI or failed articles)
        ai_articles = [r for r in results if r is not None]
        return ai_articles

    async def _phase_storage(self, articles: List[Dict[str, Any]]):
        """Phase 3: Store processed articles using the Orchestrator."""
        print(f"\n=== Phase 3: Storage (using FunctionTool) ===")
        print(f"Storing {len(articles)} AI articles...\n")
        
        if not articles:
            print("No articles to store.")
            return

        session_id = "orchestrator_session"
        storage_prompt = f"""
        Store these {len(articles)} articles using the store_articles tool.
        
        Articles: {json.dumps(articles)}
        """
        
        async for event in self.orchestrator_runner.run_async(
            user_id=self.config.user_id,
            session_id=session_id,
            new_message=types.Content(parts=[types.Part.from_text(text=storage_prompt)])
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        print(f"[Orchestrator]: {part.text}\n")

    async def run_async(self, feed_urls: List[str]):
        """Run the full hybrid pipeline."""
        print("Starting Hybrid Tool Pipeline...")
        print(f"Processing {len(feed_urls)} RSS feeds...\n")
        
        # Phase 1
        unique_articles = await self._phase_fetch_dedup(feed_urls)
        
        if not unique_articles:
            print("No articles to process. Stopping.")
            return

        # Phase 2
        ai_articles = await self._phase_process_articles(unique_articles)
        
        # Phase 3
        await self._phase_storage(ai_articles)
        
        print(f"✅ Hybrid Tool Pipeline completed!")
        print(f"   Fetched → Deduped → Filtered {len(ai_articles)}/{len(unique_articles)} AI articles → Tagged → Stored")

    def run(self, feed_urls: List[str]):
        """Synchronous wrapper for run_async."""
        return asyncio.run(self.run_async(feed_urls))

if __name__ == "__main__":
    # Test the pipeline
    pipeline = HybridToolPipeline()
    feeds = ["https://www.databricks.com/feed"]
    pipeline.run(feeds)
