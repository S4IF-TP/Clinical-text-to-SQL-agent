import time
from dataclasses import dataclass

from openai import OpenAI

from csql.config import get_settings


@dataclass
class LLMResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    latency_s: float


def chat(messages: list[dict], model: str | None = None, temperature: float = 0.0) -> LLMResult:
    """One call to any OpenAI-compatible server (Ollama, vLLM). Swap models via the string."""
    s = get_settings()
    client = OpenAI(base_url=s.llm_base_url, api_key=s.llm_api_key)
    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model or s.llm_model, messages=messages, temperature=temperature
    )
    usage = resp.usage
    return LLMResult(
        text=resp.choices[0].message.content or "",
        prompt_tokens=usage.prompt_tokens if usage else 0,
        completion_tokens=usage.completion_tokens if usage else 0,
        latency_s=time.perf_counter() - t0,
    )
