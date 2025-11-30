import re
import hashlib
from datetime import datetime
from rapidfuzz.fuzz import ratio
from typing import List, Optional
from src.models.article import Article, DeduplicationResult


def clean_text(text: str) -> str:
    """Normalize text for comparing titles and summaries."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)  # remove HTML tags
    text = re.sub(r"[\W_]+", " ", text.lower())
    return " ".join(text.split())


def stable_hash(*fields: str) -> str:
    """Stable deterministic hash for cluster_id generation."""
    raw = " ".join(fields).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def is_duplicate(article: Article,
                 processed_urls: set,
                 seen_titles: List[str],
                 seen_summaries: List[str],
                 last_fetched_at: Optional[str]) -> bool:
    """
    Multi-layer deduplication:
    - Skip items older than last_fetched_at
    - Skip URLs already seen
    - Fuzzy match title & summary
    """
    url = article.link
    title = clean_text(article.title)
    summary = clean_text(article.summary)

    # Layer 1: time-based dedup
    published = article.published
    if last_fetched_at and published and published <= last_fetched_at:
        return True

    # Layer 2: URL dedup
    if url in processed_urls:
        return True

    # Layer 3 + 4: Title + Summary fuzzy dedup
    for seen_t, seen_s in zip(seen_titles, seen_summaries):
        title_sim = ratio(title, seen_t)
        summary_sim = ratio(summary, seen_s)

        if title_sim > 90:        # strong title match
            return True

        if title_sim > 80 and summary_sim > 85:  # combined signal
            return True

    return False


def deduplicate_articles(articles: List[Article],
                         processed_urls: set,
                         last_fetched_at: Optional[str]) -> List[Article]:
    """Deduplicate a batch of articles using multi-layer logic."""
    unique = []
    seen_titles = []
    seen_summaries = []

    for article in articles:
        url = article.link

        if is_duplicate(article, processed_urls, seen_titles, seen_summaries, last_fetched_at):
            continue

        # Mark as unique
        processed_urls.add(url)
        seen_titles.append(clean_text(article.title))
        seen_summaries.append(clean_text(article.summary))

        # stable cluster_id
        article.cluster_id = url or stable_hash(article.title, article.summary)

        unique.append(article)

    return unique

def deduplicate_articles_tool(
    feed_url: str,
    articles: List[Article],
    feed_last_build_date: Optional[str] = None
) -> DeduplicationResult:
    """
    Deduplicate RSS/Atom articles for a specific feed source.

    Returns:
        DeduplicationResult object containing:
            articles: list of unique articles
            unique_count: number of unique articles
            original_count: number of original articles
            skipped: whether the feed was skipped
            feed_url: the feed URL
            last_build_date: the last build date of the feed
    """
    from src.utils.state_utils import load_state, save_state

    state = load_state()

    # Initialize feed state if missing
    feed_state = state["feeds"].get(feed_url, {
        "processed_urls": [],
        "last_fetched_at": None,
        "last_build_date": None,
    })

    stored_last_build = feed_state.get("last_build_date")
    last_fetched_at = feed_state.get("last_fetched_at")

    # Feed-level skip using lastBuildDate
    if feed_last_build_date and stored_last_build:
        if feed_last_build_date <= stored_last_build:
            return DeduplicationResult(
                articles=[],
                unique_count=0,
                original_count=len(articles),
                skipped=True,
                feed_url=feed_url,
                last_build_date=stored_last_build
            )

    # Article-level dedup
    processed_urls = set(feed_state.get("processed_urls", []))
    unique = deduplicate_articles(articles, processed_urls, last_fetched_at)

    # Update feed state
    feed_state["processed_urls"] = list(processed_urls)
    feed_state["last_fetched_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    if feed_last_build_date:
        feed_state["last_build_date"] = feed_last_build_date

    # Save global state
    state["feeds"][feed_url] = feed_state
    save_state(state)

    return DeduplicationResult(
        articles=unique,
        unique_count=len(unique),
        original_count=len(articles),
        skipped=False,
        feed_url=feed_url,
        last_build_date=feed_state.get("last_build_date")
    )



if __name__ == "__main__":
    # Test dedup
    articles = [
        {"title": "AI is great", "link": "http://example.com/1"},
        {"title": "AI is great", "link": "http://example.com/2"}, # Duplicate title
        {"title": "AI is awesome", "link": "http://example.com/1"}, # Duplicate URL
        {"title": "Something else", "link": "http://example.com/3"}
    ]
    processed = set()
    unique = deduplicate_articles(articles, processed)
    print(f"Unique: {len(unique)}")
    for a in unique:
        print(a['title'])
