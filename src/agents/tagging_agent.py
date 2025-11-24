from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.genai import types

def create_tagging_agent(model_name: str = "gemini-2.5-flash-lite", retry_config: types.HttpRetryOptions = None) -> LlmAgent:
    """
    Creates and returns the Tagging Agent.
    
    This agent adds relevant tags to AI articles.
    """
    return LlmAgent(
        name="tagging_agent",
        model=Gemini(model=model_name, retry_options=retry_config),
        instruction="""
        You are an AI news tagger. Add relevant tags to this AI article.
        
        Available tags:
        - LLM
        - Generative AI
        - AI Research
        - Enterprise AI
        - Robotics
        - AI Ethics & Governance
        - AI Infrastructure
        - AI Startups & Funding
        
        Select 1-3 most relevant tags.
        
        Respond with JSON only:
        {
            "tags": ["tag1", "tag2", "tag3"]
        }
        """
    )
