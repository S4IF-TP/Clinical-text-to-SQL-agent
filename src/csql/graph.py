from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from csql.nodes.answer import answer
from csql.nodes.correct import MAX_RETRIES, correct
from csql.nodes.execute import execute
from csql.nodes.generate import generate
from csql.nodes.guard import guard
from csql.nodes.link import link
from csql.nodes.validate import validate

# Each config is a set of optional nodes, so ablations are just removing one.
CONFIGS = {
    "baseline": dict(link=False, correct=False, guard=False),
    "link": dict(link=True, correct=False, guard=False),
    "correct": dict(link=False, correct=True, guard=False),
    "both": dict(link=True, correct=True, guard=False),
    "full": dict(link=True, correct=True, guard=True),  # production default
}


class AgentState(TypedDict, total=False):
    question: str
    model: str | None
    linked_schema: str | None
    sql: str | None
    columns: list[str]
    rows: list[Any]
    error: str | None
    answer: str | None
    trace: list[dict]
    skip_answer: bool
    retries: int
    converged: bool
    validation_failed: bool
    refused: bool


def _can_retry(state: AgentState) -> bool:
    return state.get("retries", 0) < MAX_RETRIES and not state.get("converged", False)


def _after_guard(state: AgentState) -> str:
    return "end" if state.get("refused") else "continue"


def _after_validate(state: AgentState) -> str:
    if not state.get("validation_failed"):
        return "execute"
    return "correct" if _can_retry(state) else "answer"


def _after_execute(state: AgentState) -> str:
    failed = bool(state.get("error")) or not state.get("rows")  # error or empty result
    return "correct" if failed and _can_retry(state) else "answer"


def build_graph(config: str = "full"):
    if config not in CONFIGS:
        raise ValueError(f"unknown config {config!r}; choose from {sorted(CONFIGS)}")
    cfg = CONFIGS[config]

    g = StateGraph(AgentState)
    g.add_node("generate", generate)
    g.add_node("execute", execute)
    g.add_node("answer", answer)

    entry = "generate"
    if cfg["link"]:
        g.add_node("link", link)
        g.add_edge("link", "generate")
        entry = "link"
    if cfg["guard"]:
        g.add_node("guard", guard)
        g.add_edge(START, "guard")
        g.add_conditional_edges("guard", _after_guard, {"end": END, "continue": entry})
    else:
        g.add_edge(START, entry)

    if cfg["correct"]:
        g.add_node("validate", validate)
        g.add_node("correct", correct)
        g.add_edge("generate", "validate")
        g.add_conditional_edges(
            "validate",
            _after_validate,
            {"execute": "execute", "correct": "correct", "answer": "answer"},
        )
        g.add_edge("correct", "validate")
        g.add_conditional_edges(
            "execute", _after_execute, {"correct": "correct", "answer": "answer"}
        )
    else:
        g.add_edge("generate", "execute")
        g.add_edge("execute", "answer")
    g.add_edge("answer", END)
    return g.compile()


def ask(
    question: str, model: str | None = None, config: str = "full", with_answer: bool = True
) -> AgentState:
    return build_graph(config).invoke(
        {"question": question, "model": model, "trace": [], "skip_answer": not with_answer}
    )
