"""
Main entry point for the Hybrid Tool Pipeline.

This version combines:
- FunctionTools for utilities (fetch, dedup, storage)
- SequentialAgent for LLM processing (filter + tag each article)
- Best of both worlds!
"""

from dotenv import load_dotenv
from src.pipeline import HybridToolPipeline
from src.utils.logger import setup_logging

if __name__ == "__main__":
    load_dotenv()
    
    # Initialize logging
    setup_logging()
    
    # Default feeds
    feeds = [
        "https://www.databricks.com/feed",
        # "https://techcrunch.com/feed/",
        # "https://developers.googleblog.com/feeds/posts/default"
    ]
    
    pipeline = HybridToolPipeline()
    pipeline.run(feeds)
