import difflib
from typing import List, Dict, Any

def deduplicate_articles(articles: List[Dict[str, Any]], processed_urls: set) -> List[Dict[str, Any]]:
    """
    Deduplicates articles based on URL and title similarity.

    Args:
        articles: List of article dictionaries.
        processed_urls: Set of already processed URLs.

    Returns:
        List of unique articles with 'cluster_id' assigned.
    """
    unique_articles = []
    seen_titles = []

    for article in articles:
        url = article.get("link")
        title = article.get("title")

        # 1. Check URL exact match
        if url in processed_urls:
            continue
        
        # 2. Check title similarity
        is_duplicate = False
        for seen_title in seen_titles:
            similarity = difflib.SequenceMatcher(None, title, seen_title).ratio()
            if similarity > 0.85:
                is_duplicate = True
                break
        
        if is_duplicate:
            continue

        # If unique
        processed_urls.add(url)
        seen_titles.append(title)
        # Assign a simple cluster ID (for now just using index or hash could be enough, 
        # but here we just mark it as unique. The prompt mentions cluster_ids, 
        # so we can generate a UUID or just pass it through.)
        # For simplicity, we'll just return the article as is, 
        # assuming the calling agent might handle clustering more deeply if needed.
        # But let's add a placeholder cluster_id.
        article['cluster_id'] = str(hash(title)) 
        unique_articles.append(article)

    return unique_articles

def deduplicate_articles_tool(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Deduplicate articles based on title similarity and processed URLs.
    
    Args:
        articles: List of article dictionaries to deduplicate.
    
    Returns:
        Dictionary with unique 'articles' list and counts.
    """
    from src.tools.storage import load_state
    
    # Load processed URLs from state
    state = load_state()
    processed_urls = set(state.get("processed_urls", []))
    
    # Deduplicate
    unique_articles = deduplicate_articles(articles, processed_urls)
    
    return {
        "articles": unique_articles,
        "unique_count": len(unique_articles),
        "original_count": len(articles),
        "status": "success"
    }

# Create FunctionTool instance
from google.adk.tools import FunctionTool
dedup_tool = FunctionTool(deduplicate_articles_tool)

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
