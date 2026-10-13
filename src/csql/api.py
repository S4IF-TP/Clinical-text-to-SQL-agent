from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from csql.graph import ask

app = FastAPI(title="Clinical Text-to-SQL Agent")


class AskRequest(BaseModel):
    question: str
    model: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ask")
def ask_endpoint(req: AskRequest) -> dict:
    """Returns {sql, columns, rows, answer, trace, refused, error}."""
    try:
        state = ask(req.question, model=req.model)
    except Exception as e:  # LLM unreachable, bad key, etc.
        return {
            "sql": None,
            "columns": [],
            "rows": [],
            "answer": None,
            "trace": [],
            "refused": False,
            "error": f"{type(e).__name__}: {e}",
        }
    return jsonable_encoder(
        {
            "sql": state.get("sql"),
            "columns": state.get("columns", []),
            "rows": state.get("rows", []),
            "answer": state.get("answer"),
            "trace": state.get("trace", []),
            "refused": state.get("refused", False),
            "error": state.get("error"),
        }
    )
