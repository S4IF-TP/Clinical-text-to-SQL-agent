import argparse

from csql.graph import ask


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="csql", description="Ask a question about the clinical DB"
    )
    parser.add_argument("question")
    parser.add_argument("--model", default=None, help="override LLM_MODEL")
    args = parser.parse_args()

    state = ask(args.question, model=args.model)
    print("SQL:\n" + state["sql"])
    if state.get("error"):
        print("\nERROR:", state["error"])
    else:
        print(f"\nRows ({len(state['rows'])}, showing up to 10):")
        print(state["columns"])
        for row in state["rows"][:10]:
            print(row)
    print("\nAnswer:", state["answer"])


if __name__ == "__main__":
    main()
