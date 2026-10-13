"""Evaluate the guard on its own 40-case set (20 refusal + 20 legit) plus the 90 benchmark questions.

Usage: uv run python bench/eval_guard.py --model openai/gpt-oss-120b
Reports LLM+fallback guard vs keyword-only baseline; writes bench/results/guard_<model>.md
"""

import argparse
import json
from pathlib import Path

from csql.nodes.guard import classify, keyword_label

ROOT = Path(__file__).parent


def load(name: str) -> list[dict]:
    return [json.loads(x) for x in (ROOT / name).read_text("utf-8").splitlines() if x]


def metrics(preds: list[tuple[str, str]]) -> dict:
    """preds = [(gold, pred)], positive class = medical_advice (should be refused)."""
    tp = sum(g == p == "medical_advice" for g, p in preds)
    fp = sum(g == "data_question" and p == "medical_advice" for g, p in preds)
    fn = sum(g == "medical_advice" and p == "data_question" for g, p in preds)
    tn = sum(g == p == "data_question" for g, p in preds)
    return {"acc": (tp + tn) / len(preds), "refusal_recall": tp / max(tp + fn, 1),
            "precision": tp / max(tp + fp, 1), "tp": tp, "fp": fp, "fn": fn, "tn": tn}  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    args = ap.parse_args()

    cases = load("guard_set.jsonl")
    llm, kw, errors = [], [], []
    for c in cases:
        label, method, _ = classify(c["question"], args.model)
        llm.append((c["label"], label))
        kw.append((c["label"], keyword_label(c["question"])))
        if label != c["label"]:
            errors.append(f"- `{c['id']}` ({method}) expected {c['label']}: {c['question']}")

    bench = load("questions.jsonl")
    wrongly_refused = [
        q["id"] for q in bench if classify(q["question"], args.model)[0] == "medical_advice"
    ]

    m_llm, m_kw = metrics(llm), metrics(kw)
    lines = [
        f"# Guard evaluation — {args.model}\n",
        "| Guard | Accuracy | Refusal recall | Precision | TP | FP | FN | TN |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, m in (("LLM (+keyword fallback)", m_llm), ("Keywords only", m_kw)):
        lines.append(
            f"| {name} | {m['acc']:.1%} | {m['refusal_recall']:.1%} | {m['precision']:.1%} | "
            f"{m['tp']} | {m['fp']} | {m['fn']} | {m['tn']} |"
        )
    lines.append(
        f"\nFalse refusals on the {len(bench)} benchmark questions: "
        f"{len(wrongly_refused)} {wrongly_refused or ''}\n"
    )
    if errors:
        lines.append("Misclassified by the LLM guard:\n" + "\n".join(errors))
    text = "\n".join(lines)
    out = ROOT / "results" / f"guard_{args.model.replace('/', '_')}.md"
    out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
