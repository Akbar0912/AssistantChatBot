from dataclasses import dataclass

@dataclass
class LLMConfig:
    model: str = "llama3.2"
    temperature: float = 0.1
    top_p: float = 0.95
    top_k: int = 40
    repeat_penalty: float = 1.1
    timeout: int = 30