from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from csql.nodes.answer import answer
from csql.nodes.execute import execute
from csql.nodes.generate import generate


class AgentState(TypedDict, total=False):
    question: str
    model: str | None
    sql: str
    columns: list[str]
    rows: list[Any]
    error: str | None
    answer: str
    trace: list[dict]
    skip_answer: bool


def build_graph():
    """Baseline (v0.1): generate -> execute -> answer. No linking, validation or retry."""
    g = StateGraph(AgentState)
    g.add_node("generate", generate)
    g.add_node("execute", execute)
    g.add_node("answer", answer)
    g.add_edge(START, "generate")
    g.add_edge("generate", "execute")
    g.add_edge("execute", "answer")
    g.add_edge("answer", END)
    return g.compile()


def ask(
    question: str, model: str | None = None, config: str = "baseline", with_answer: bool = True
) -> AgentState:
    if config != "baseline":
        raise ValueError(f"unknown config {config!r}")
    return build_graph().invoke(
        {"question": question, "model": model, "trace": [], "skip_answer": not with_answer}
    )
