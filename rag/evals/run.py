import json
import sys
import time
from pathlib import Path

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import EvaluatorContext

from rag.knowledge import MAX_DISTANCE
from rag.store import search

QUESTIONS = Path(__file__).parent / "questions.jsonl"
K = 5
PAUSE = 3.0


def load_cases() -> list[Case]:
    cases = []
    for line in QUESTIONS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        cases.append(
            Case(
                name=row["id"],
                inputs=row["question"],
                expected_output=row["expected"],
                metadata={
                    "lang": row["lang"],
                    "answerable": row["answerable"],
                    "kind": row.get("kind"),
                },
            )
        )
    return cases


def retrieve(question: str) -> dict:
    time.sleep(PAUSE)
    hits = search(question, k=K)
    ranked = {}
    for doc, distance in hits:
        ranked.setdefault(doc.metadata.get("doc_id"), distance)
    best = min(ranked.values()) if ranked else 9.9
    return {"ids": list(ranked), "best": best}


def ranking(ctx: EvaluatorContext[str, dict, dict]) -> dict:
    if not ctx.metadata["answerable"]:
        return {
            "refused": ctx.output["best"] > MAX_DISTANCE,
            "best": ctx.output["best"],
        }
    ids = ctx.output["ids"]
    rank = next((i for i, d in enumerate(ids, 1) if d in ctx.expected_output), None)
    return {
        "hit@1": rank == 1,
        "hit@3": rank is not None and rank <= 3,
        f"recall@{K}": rank is not None,
        "mrr": 1 / rank if rank else 0.0,
    }


def main() -> None:
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    dataset = Dataset(name="notes-retrieval", cases=load_cases(), evaluators=[ranking])
    report = dataset.evaluate_sync(retrieve, name=label, max_concurrency=1)
    report.print(include_input=True, include_output=False, include_durations=False)


if __name__ == "__main__":
    main()
