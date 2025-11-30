from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class Article(BaseModel):
    """Represents a single news article from an RSS feed."""
    
    feed_url: str = Field(..., description="Source RSS feed URL")
    title: str = Field(..., description="Article title")
    link: str = Field(..., description="Article URL")
    summary: str = Field(default="", description="Article summary/description")
    published: Optional[str] = Field(None, description="Publication timestamp")
    source: str = Field(default="", description="Feed/publication name")
    cluster_id: Optional[str] = Field(None, description="Unique identifier for deduplication")
    tags: List[str] = Field(default_factory=list, description="AI-generated tags")
    
    class Config:
        json_schema_extra = {
            "example": {
                "feed_url": "https://example.com/feed",
                "title": "AI Breakthrough in 2024",
                "link": "https://example.com/article",
                "summary": "New developments in AI...",
                "published": "2024-11-30 12:00:00",
                "source": "Tech News",
                "cluster_id": "abc123",
                "tags": ["AI", "Machine Learning"]
            }
        }


class FeedMetadata(BaseModel):
    """Metadata about an RSS feed."""
    
    feed_url: str = Field(..., description="RSS feed URL")
    last_build_date: Optional[str] = Field(None, description="Feed's last build date")
    

class FeedResult(BaseModel):
    """Result from fetching an RSS feed."""
    
    feed_url: str = Field(..., description="RSS feed URL")
    last_build_date: Optional[str] = Field(None, description="Feed's last build date")
    articles: List[Article] = Field(default_factory=list, description="Fetched articles")


class DeduplicationResult(BaseModel):
    """Result from article deduplication."""
    
    articles: List[Article] = Field(default_factory=list, description="Unique articles")
    unique_count: int = Field(..., description="Number of unique articles")
    original_count: int = Field(..., description="Original article count")
    skipped: bool = Field(default=False, description="Whether dedup was skipped")
    feed_url: str = Field(..., description="Source feed URL")
    last_build_date: Optional[str] = Field(None, description="Feed's last build date")


class FilterResult(BaseModel):
    """Result from AI filtering."""
    
    is_ai: bool = Field(..., description="Whether article is AI-related")
    reasoning: str = Field(default="", description="Explanation for the decision")


class TagResult(BaseModel):
    """Result from AI tagging."""
    
    tags: List[str] = Field(default_factory=list, description="Generated tags")
