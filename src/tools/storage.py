import json
import os
from typing import List
from src.models.article import Article

DATA_DIR = "data"
ARTICLES_FILE = os.path.join(DATA_DIR, "ai_articles.jsonl")

# ---------------------------------------------------------------------
# Article Storage
# ---------------------------------------------------------------------

def store_articles(articles: List[Article]):
    """
    Append new articles to ai_articles.jsonl.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    # Write JSONL
    with open(ARTICLES_FILE, "a", encoding="utf-8") as f:
        for article in articles:
            f.write(article.model_dump_json() + "\n")


if __name__ == "__main__":
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    test_articles = [
        {"title": "Test", "summary": "Example", "link": "http://example.com/1", "cluster_id": "abc123"}
    ]
    store_articles(test_articles)
