"""Score retrieval against eval/questions.yaml.

For each question: did any expected training appear in the top k results, and
at what rank? Reports hit@k and mean reciprocal rank (MRR), plus the misses,
so changes to chunking or ranking can be compared run to run.
"""
from __future__ import annotations

from ..catalog import ROOT, read_yaml
from .index import search

QUESTIONS = ROOT / "eval" / "questions.yaml"


def evaluate(k: int = 5, verbose: bool = False) -> dict:
    questions = read_yaml(QUESTIONS)
    hits, rr, misses = 0, 0.0, []
    for item in questions:
        results = search(item["q"], k=k)
        ranked = [h.chunk["training_id"] for h in results]
        rank = next((i for i, t in enumerate(ranked, 1) if t in item["expect"]), None)
        if rank:
            hits += 1
            rr += 1 / rank
        else:
            misses.append((item["q"], ranked[:3]))
        if verbose:
            print(f"{'ok ' if rank else 'MISS'} {rank or '-'}  {item['q']}")
    n = len(questions)
    print(f"\nhit@{k}: {hits}/{n} ({hits / n:.0%})   MRR: {rr / n:.2f}")
    for q, got in misses:
        print(f"  miss: {q}\n        got: {', '.join(got)}")
    return {"hit": hits / n, "mrr": rr / n}
