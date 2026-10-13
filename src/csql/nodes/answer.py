from csql.llm import chat

SYSTEM = (
    "You answer clinician questions using the SQL result provided. Reply in 1-3 plain sentences "
    "stating only what the result shows. If the query failed or returned no rows, say so honestly."
)


def answer(state: dict) -> dict:
    trace = state.get("trace", [])
    if state.get("error"):
        text = f"The query failed: {state['error']}"
        return {"answer": text, "trace": trace + [{"node": "answer", "llm": False}]}

    preview = "\n".join(str(r) for r in state["rows"][:20])
    res = chat(
        [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"Question: {state['question']}\nSQL: {state['sql']}\n"
                f"Columns: {state['columns']}\nRows (first 20 of {len(state['rows'])}):\n{preview}",
            },
        ],
        model=state.get("model"),
    )
    return {
        "answer": res.text.strip(),
        "trace": trace
        + [
            {
                "node": "answer",
                "latency_s": round(res.latency_s, 2),
                "tokens": res.prompt_tokens + res.completion_tokens,
            }
        ],
    }
