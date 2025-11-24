import json
import os
from typing import List, Dict, Any
from datetime import datetime

DATA_DIR = "data"
ARTICLES_FILE = os.path.join(DATA_DIR, "ai_articles.jsonl")
STATE_FILE = os.path.join(DATA_DIR, "state.json")

def load_state() -> Dict[str, Any]:
    """Loads the state from state.json."""
    if not os.path.exists(STATE_FILE):
        return {"processed_urls": [], "last_fetched_at": None}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"processed_urls": [], "last_fetched_at": None}

def save_state(state: Dict[str, Any]):
    """Saves the state to state.json."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def store_articles(articles: List[Dict[str, Any]], state: Dict[str, Any]):
    """
    Stores articles to ai_articles.jsonl and updates state.

    Args:
        articles: List of articles to store.
        state: Current state dictionary.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    # Append articles to JSONL
    with open(ARTICLES_FILE, "a", encoding="utf-8") as f:
        for article in articles:
            f.write(json.dumps(article, ensure_ascii=False) + "\n")
            f.flush()
    
    # Update state
    # We assume 'processed_urls' is a list in the JSON file, but a set in memory for efficiency.
    # Here we just append the new URLs.
    current_urls = set(state.get("processed_urls", []))
    for article in articles:
        current_urls.add(article["link"])
    
    state["processed_urls"] = list(current_urls)
    state["last_fetched_at"] = datetime.now().isoformat()
    
    save_state(state)

def store_articles_tool(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Store articles to JSON file.
    
    Args:
        articles: List of article dictionaries to store.
    
    Returns:
        Dictionary with storage status and count.
    """
    if not articles:
        return {"stored_count": 0, "status": "no articles"}
        
    state = load_state()
    store_articles(articles, state)
    
    return {
        "stored_count": len(articles),
        "status": "success"
    }

# Create FunctionTool instance
from google.adk.tools import FunctionTool
storage_tool = FunctionTool(store_articles_tool)

if __name__ == "__main__":
    # Test storage
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    state = load_state()
    print(f"Initial state: {state}")
    
    new_articles = [
        {"title": "Test Article", "link": "http://test.com/1", "cluster_id": "123"}
    ]
    store_articles(new_articles, state)
    
    updated_state = load_state()
    print(f"Updated state: {updated_state}")
