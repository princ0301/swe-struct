from pydantic import BaseModel

class Limits(BaseModel):
    max_steps: int = 30
    max_tool_output_chars: int = 6000