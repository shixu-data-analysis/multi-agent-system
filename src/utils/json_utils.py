import json
from typing import Optional, Any, TypeVar, Type
from pydantic import BaseModel, ValidationError
from src.utils.logger import get_logger

logger = get_logger(__name__)
T = TypeVar('T', bound=BaseModel)

def parse_json_safe(text: str) -> Optional[Any]:
    """Extract JSON from raw or markdown-wrapped LLM output."""
    try:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception:
        return None


def parse_pydantic_safe(text: str, model: Type[T]) -> Optional[T]:
    """Parse JSON text into a Pydantic model with error handling."""
    try:
        data = parse_json_safe(text)
        if data is None:
            return None
        return model.model_validate(data)
    except ValidationError as e:
        logger.error(f"Validation error parsing {model.__name__}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error parsing {model.__name__}: {e}")
        return None
