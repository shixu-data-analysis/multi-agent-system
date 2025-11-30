import feedparser
import concurrent.futures
from typing import List
from src.utils.date_utils import normalize_rss_timestamp
from src.models.article import Article, FeedResult
from src.utils.logger import get_logger

logger = get_logger(__name__)

def fetch_rss(feed_url: str) -> FeedResult:
    """
    Fetch and parse a single RSS/Atom feed.

    Returns a FeedResult containing:
        - feed_url
        - last_build_date (RSS <lastBuildDate> or Atom <updated>)
        - articles: list of Article objects
    """
    try:
        feed = feedparser.parse(feed_url)

        raw_last_build_date = feed.feed.get("updated_parsed")

        articles = []
        for entry in feed.entries:
            raw_published = entry.get("published_parsed") or entry.get("updated_parsed")
            article = Article(
                feed_url=feed_url,
                title=entry.get("title", ""),
                link=entry.get("link", ""),
                summary=entry.get("summary", "") or entry.get("description", ""),
                published=normalize_rss_timestamp(raw_published),
                source=feed.feed.get("title", "")
            )
            articles.append(article)

        return FeedResult(
            feed_url=feed_url,
            last_build_date=normalize_rss_timestamp(raw_last_build_date),
            articles=articles
        )

    except Exception as e:
        logger.error(f"Error fetching {feed_url}: {e}")
        return FeedResult(
            feed_url=feed_url,
            last_build_date=None,
            articles=[]
        )


def fetch_all_rss(feed_urls: List[str]) -> List[FeedResult]:
    """
    Fetch multiple RSS feeds in parallel.

    Returns a list of FeedResult objects.
    """
    results = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch_rss, url): url for url in feed_urls}

        for future in concurrent.futures.as_completed(futures):
            feed_url = futures[future]
            try:
                result = future.result()
                logger.info(f"Fetched {len(result.articles)} items from {feed_url}")
                results.append(result)
            except Exception as e:
                logger.error(f"Error fetching {feed_url}: {e}")
                results.append(FeedResult(
                    feed_url=feed_url,
                    last_build_date=None,
                    articles=[]
                ))

    return results


# Manual test: optional
if __name__ == "__main__":
    urls = [
        "https://techcrunch.com/feed/",
        "https://developers.googleblog.com/feeds/posts/default",
    ]
    results = fetch_all_rss(urls)
    for result in results:
        print(f"{result.feed_url}: {len(result.articles)} articles")
