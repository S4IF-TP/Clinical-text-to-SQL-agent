"""Guard: refuse diagnosis / treatment requests; only answer questions about the data."""

import re

from csql.llm import chat

REFUSAL = (
    "I can only answer questions about the records in this database (counts, trends, lists). "
    "I can't give diagnoses, treatment or medication advice — please consult a clinician."
)

SYSTEM = """Classify the user's message for a clinical DATABASE assistant.
- data_question: asks about records in the database (counts, averages, lists, trends, comparisons),
  even when it mentions diseases, drugs or procedures.
- medical_advice: asks for a diagnosis, treatment, dosage, prognosis or any recommendation about what
  a person or patient should do, take, or receive.
Reply with exactly one word: data_question or medical_advice."""

# Fallback when the LLM is unreachable or answers off-format.
ADVICE_PATTERNS = [
    r"\bshould (i|we|he|she|they|the patient)\b",
    r"\bdo i have\b",
    r"\bam i (sick|dying|at risk|pregnant|diabetic)\b",
    r"\bwhat (is|are) (the )?(best|right|correct) (treatment|medication|drug|dose|dosage)\b",
    r"\bwhat (dose|dosage)\b",
    r"\bhow (do|can|should) (i|we) (treat|cure|manage|lower|reduce)\b",
    r"\b(diagnose|prescribe|recommend)\b.*\b(me|him|her|them|patient)\b",
    r"\b(cure|treat) my\b",
    r"\bmy (symptoms?|pain|doctor|blood pressure|medication)\b",
    r"\bis it safe (for me|to take)\b",
    r"\bcan i take\b",
    r"\bwhat (should|can) i (take|do|eat)\b",
    r"\bwhich (drug|medication|treatment) should\b",
    r"\bdrug interaction\b.*\b(safe|take)\b",
]
_ADVICE_RE = re.compile("|".join(ADVICE_PATTERNS), re.IGNORECASE)


def keyword_label(question: str) -> str:
    return "medical_advice" if _ADVICE_RE.search(question) else "data_question"


def classify(question: str, model: str | None = None) -> tuple[str, str, int]:
    """Return (label, method, tokens). LLM first; keyword fallback if it fails or is off-format."""
    try:
        res = chat(
            [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}],
            model=model,
        )
        text = res.text.strip().lower()
        tokens = res.prompt_tokens + res.completion_tokens
        if "medical_advice" in text:
            return "medical_advice", "llm", tokens
        if "data_question" in text:
            return "data_question", "llm", tokens
        return keyword_label(question), "keyword_fallback", tokens
    except Exception:
        return keyword_label(question), "keyword_fallback", 0


def guard(state: dict) -> dict:
    label, method, tokens = classify(state["question"], state.get("model"))
    entry = {"node": "guard", "label": label, "method": method, "tokens": tokens}
    out = {"trace": state.get("trace", []) + [entry]}
    if label == "medical_advice":
        out |= {"refused": True, "answer": REFUSAL, "sql": None}
    return out
