from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.genai import types
from src.tools.fetch_rss import fetch_tool
from src.tools.dedup import dedup_tool
from src.tools.storage import storage_tool

def create_orchestrator(model_name: str = "gemini-2.5-flash-lite", retry_config: types.HttpRetryOptions = None) -> LlmAgent:
    """
    Creates and returns the Pipeline Orchestrator Agent.
    
    This agent coordinates the fetching, deduplication, and storage of articles.
    """
    return LlmAgent(
        name="pipeline_orchestrator",
        model=Gemini(model=model_name, retry_options=retry_config),
        tools=[fetch_tool, dedup_tool, storage_tool],
        instruction="""
        You are an AI news pipeline orchestrator.
        
        Your workflow:
        1. Use fetch_rss_articles to get articles from RSS feeds
        2. Use deduplicate_articles to remove duplicates
        3. Tell me when articles are ready for LLM processing
        4. After LLM processing, use store_articles to save results
        
        Always use the tools for fetch, dedup, and storage.
        """
    )
