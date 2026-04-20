from typing import Dict

from pydantic import BaseModel, Field


class LLMCall(BaseModel):
    """
    LLM call model for storing LLM call information.
    """

    model_name: str = Field(default="", description="Model name")
    timestamp: str = Field(default="", description="Timestamp")
    total_tokens: int = Field(default=0, description="Total tokens")
    input_tokens: int = Field(default=0, description="Input tokens")
    output_tokens: int = Field(default=0, description="Output tokens")
    total_cost: float = Field(default=0.0, description="Total cost")
    prompts: Dict[str, str] = Field(default=None, description="Prompts")
    parsed_reply: str = Field(default="", description="Parsed reply")
