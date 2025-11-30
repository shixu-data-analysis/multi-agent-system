import json
import os
from typing import Dict, Any

DATA_DIR = "data"
STATE_FILE = os.path.join(DATA_DIR, "state.json")

DEFAULT_FEED_STATE = {
    "processed_urls": [],     # canonical URLs seen so far
    "last_fetched_at": None,  # ISO time string
    "last_build_date": None,  # lastBuildDate from feed
}

def load_state() -> Dict[str, Any]:
    """Load persistent state. Initialize per-feed container."""
    if not os.path.exists(STATE_FILE):
        return {"feeds": {}}

    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            data.setdefault("feeds", {})
            return data
    except json.JSONDecodeError:
        return {"feeds": {}}


def save_state(state: Dict[str, Any]):
    """Persist state to disk."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
