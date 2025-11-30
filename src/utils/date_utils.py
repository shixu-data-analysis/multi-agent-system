from time import struct_time
from calendar import timegm
from datetime import datetime, timezone
from typing import Optional

def normalize_rss_timestamp(parsed_st: struct_time) -> Optional[str]:
    """
    Convert a struct_time (from feedparser) to an ISO 8601 string (UTC).
    Returns None if input is None or conversion fails.
    """
    if parsed_st:
        try:
            dt = datetime.fromtimestamp(timegm(parsed_st), tz=timezone.utc)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    return None
