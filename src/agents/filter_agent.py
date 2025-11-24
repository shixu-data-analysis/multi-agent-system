from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.genai import types

def create_filter_agent(model_name: str = "gemini-2.5-flash-lite", retry_config: types.HttpRetryOptions = None) -> LlmAgent:
    """
    Creates and returns the Filter Agent.
    
    This agent analyzes articles to determine if they are AI-related.
    """
    return LlmAgent(
        name="filter_agent",
        model=Gemini(model=model_name, retry_options=retry_config),
        instruction="""
        You are an AI news filter. Analyze the article and determine if it's AI-related.
        
        Keywords: AI, artificial intelligence, machine learning, ML, deep learning, 
        large language model, LLM, generative AI, GenAI, GPT, Gemini, 
        robotics, foundation model, neural network
        
        Respond with JSON only:
        {
            "is_ai": true/false,
            "reasoning": "brief explanation"
        }
        """
    )
