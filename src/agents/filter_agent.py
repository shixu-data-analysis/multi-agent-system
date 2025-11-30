from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.genai import types
from src.config.agent_config import AI_KEYWORDS

def create_filter_agent(model_name: str = "gemini-2.5-flash-lite", retry_config: types.HttpRetryOptions = None) -> LlmAgent:
    """
    Creates and returns the Filter Agent.
    
    This agent analyzes articles to determine if they are AI-related.
    """
    keywords_str = ", ".join(AI_KEYWORDS)
    
    return LlmAgent(
        name="filter_agent",
        model=Gemini(model=model_name, retry_options=retry_config),
        instruction=f"""
        You are an AI news filter. Analyze the article and determine if it's AI-related.
        
        Keywords: {keywords_str}
        
        Respond with JSON only:
        {{
            "is_ai": true/false,
            "reasoning": "brief explanation"
        }}
        """
    )
