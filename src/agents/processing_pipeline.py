from google.adk.agents import SequentialAgent
from google.genai import types
from src.agents.filter_agent import create_filter_agent
from src.agents.tagging_agent import create_tagging_agent

def create_processing_pipeline(model_name: str = "gemini-2.5-flash-lite", retry_config: types.HttpRetryOptions = None) -> SequentialAgent:
    """
    Creates and returns the Sequential Processing Pipeline.
    
    This pipeline consists of:
    1. Filter Agent: Determines if article is AI-related.
    2. Tagging Agent: Adds tags to AI articles.
    """
    filter_agent = create_filter_agent(model_name, retry_config)
    tagging_agent = create_tagging_agent(model_name, retry_config)
    
    return SequentialAgent(
        name="llm_processing_pipeline",
        sub_agents=[
            filter_agent,
            tagging_agent
        ]
    )
