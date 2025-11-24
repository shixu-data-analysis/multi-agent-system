import feedparser
import concurrent.futures
from typing import List, Dict, Any

def fetch_rss(feed_url: str) -> List[Dict[str, Any]]:
    """
    Fetches and parses an RSS feed.

    Args:
        feed_url: The URL of the RSS feed.

    Returns:
        A list of dictionaries, where each dictionary represents an article
        and contains keys like 'title', 'link', 'summary', 'published', 'source'.
    """
    try:
        feed = feedparser.parse(feed_url)
        articles = []
        for entry in feed.entries:
            article = {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", "") or entry.get("description", ""),
                "published": entry.get("published", "") or entry.get("updated", ""),
                "source": feed.feed.get("title", "")
            }
            articles.append(article)
        return articles
    except Exception as e:
        print(f"Error fetching {feed_url}: {e}")
        return []

def fetch_all_rss(feed_urls: List[str]) -> List[Dict[str, Any]]:
    """
    Fetches articles from multiple RSS feeds in parallel.

    Args:
        feed_urls: List of RSS feed URLs.

    Returns:
        A flat list of all fetched articles.
    """
    all_articles = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_url = {executor.submit(fetch_rss, url): url for url in feed_urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                articles = future.result()
                all_articles.extend(articles)
                print(f"Fetched {len(articles)} items from {url}")
            except Exception as e:
                print(f"Error fetching {url}: {e}")
    
    return all_articles

def fetch_rss_articles(feed_urls: List[str]) -> Dict[str, Any]:
    """
    Fetch articles from RSS feeds.
    
    Args:
        feed_urls: List of RSS feed URLs to fetch from.
    
    Returns:
        Dictionary with 'articles' list and 'count' of fetched articles.
    """
    articles = fetch_all_rss(feed_urls)
    
    return {
        "articles": articles,
        "count": len(articles),
        "status": "success"
    }

# Create FunctionTool instance
from google.adk.tools import FunctionTool
fetch_tool = FunctionTool(fetch_rss_articles)

if __name__ == "__main__":
    # Test with a sample feed
    urls = [
        "https://techcrunch.com/feed/",
        "https://developers.googleblog.com/feeds/posts/default"
    ]
    items = fetch_all_rss(urls)
    print(f"Total fetched: {len(items)}")
    if items:
        print(items[0])
