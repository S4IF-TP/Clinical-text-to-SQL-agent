import re
import time
from dataclasses import dataclass

from openai import OpenAI, RateLimitError

from csql.config import get_settings

MAX_RATE_LIMIT_WAITS = 30  # free tiers (e.g. Groq tokens-per-day) recover on a rolling window


def _retry_after_seconds(message: str) -> float | None:
    """Parse 'Please try again in 3m6.6s' from a 429 body; None if it is not a wait-able limit."""
    if "Request too large" in message:
        return None
    m = re.search(r"try again in (?:(\d+)m)?(?:([\d.]+)s)?", message)
    if not m or not (m.group(1) or m.group(2)):
        return None
    return int(m.group(1) or 0) * 60 + float(m.group(2) or 0)


@dataclass
class LLMResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    latency_s: float


def chat(messages: list[dict], model: str | None = None, temperature: float = 0.0) -> LLMResult:
    """One call to any OpenAI-compatible server (Ollama, vLLM). Swap models via the string."""
    s = get_settings()
    client = OpenAI(base_url=s.llm_base_url, api_key=s.llm_api_key, max_retries=8)
    for attempt in range(MAX_RATE_LIMIT_WAITS + 1):
        t0 = time.perf_counter()  # restarted per attempt: waiting out a rate limit is not latency
        try:
            resp = client.chat.completions.create(
                model=model or s.llm_model, messages=messages, temperature=temperature
            )
            break
        except RateLimitError as e:
            wait = _retry_after_seconds(str(e))
            if wait is None or attempt == MAX_RATE_LIMIT_WAITS:
                raise
            time.sleep(wait + 1)
    usage = resp.usage
    return LLMResult(
        text=resp.choices[0].message.content or "",
        prompt_tokens=usage.prompt_tokens if usage else 0,
        completion_tokens=usage.completion_tokens if usage else 0,
        latency_s=time.perf_counter() - t0,
    )
