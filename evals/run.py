"""
Eval runner. Run from the repo root:

  python -m evals.run retrieval                 # no LLM calls
  python -m evals.run posts --n 3               # 3 samples per case
  python -m evals.run replies --model some/model --judge-model other/model
  python -m evals.run all --no-judge            # deterministic checks only

Nothing is posted anywhere. Full records are written to evals/results/.
The company context is fetched from Notion unless --context-file is given.
"""
import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from statistics import mean

from chunking import chunk_document
from generate_replies import generate_replies
from llm import DEFAULT_MODEL
from post_generator import generate_post
from retrieval import build_context, retrieve_top_k
from evals.checks import check_post, check_replies
from evals.judge import MIN_PASSING_SCORE, POST_RUBRIC, REPLY_RUBRIC, judge

HERE = Path(__file__).parent

# first entry is what retrieval.build_context uses
CHUNK_CONFIGS = [
    ("paragraph", {"target_chars": 500}),
    ("sentences", {"sentences_per_chunk": 4}),
    ("chars", {"size": 500}),
]
KS = (1, 3, 6)


def load_cases(name: str) -> list[dict]:
    return json.loads((HERE / "cases" / f"{name}.json").read_text(encoding="utf-8"))


def _error(e: Exception) -> str:
    return f"{type(e).__name__}: {e}"


def _add_judgement(rec: dict, rubric: dict, materials: list[str], judge_model: str) -> None:
    try:
        verdicts = [judge(rubric, m, judge_model) for m in materials]
    except Exception as e:
        rec["judge_error"] = _error(e)
        return
    rec["judge"] = {
        "scores": {c: mean(v["scores"][c] for v in verdicts) for c in rubric},
        "verdicts": verdicts,
    }


def passed(rec: dict) -> bool:
    if "error" in rec or not all(rec["checks"].values()):
        return False
    scores = rec.get("judge", {}).get("scores", {})
    return all(s >= MIN_PASSING_SCORE for s in scores.values())


def run_posts(document: str, n: int, model: str | None, judge_model: str | None) -> list[dict]:
    context = build_context(document)
    records = []
    for case in load_cases("posts"):
        for i in range(n):
            rec = {"case": case["id"], "sample": i}
            records.append(rec)
            try:
                post = generate_post(context, topic=case["topic"], max_words=case["max_words"], model=model)
            except Exception as e:
                rec["error"] = _error(e)
                continue
            rec["output"] = post
            rec["checks"] = check_post(post, case["max_words"])
            if judge_model:
                material = f"Company context:\n{context}\n\nRequested topic: {case['topic']}\n\nPost to score:\n{post}"
                _add_judgement(rec, POST_RUBRIC, [material], judge_model)
            print("." if passed(rec) else "F", end="", flush=True)
    print()
    return records


def run_replies(n: int, model: str | None, judge_model: str | None) -> list[dict]:
    cases = load_cases("replies")
    # the generator only ever sees the normalized status shape from mastodon_fetch
    statuses = [{k: v for k, v in s.items() if k != "expect_review"} for s in cases]
    by_id = {s["id"]: s for s in statuses}
    records = []
    for i in range(n):
        rec = {"case": "batch", "sample": i}
        records.append(rec)
        try:
            batch = generate_replies(statuses, model=model)
        except Exception as e:  # includes the model returning invalid JSON
            rec["error"] = _error(e)
            continue
        rec["output"] = batch
        rec["checks"] = check_replies(cases, batch)
        if judge_model and rec["checks"]["schema_ok"]:
            materials = [
                f"Status being replied to:\n{by_id[r['in_reply_to_id']]['content_text']}\n\nReply to score:\n{r['reply_text']}"
                for r in batch["replies"]
                if r["in_reply_to_id"] in by_id
            ]
            if materials:
                _add_judgement(rec, REPLY_RUBRIC, materials, judge_model)
        print("." if passed(rec) else "F", end="", flush=True)
    print()
    return records


def run_retrieval(document: str) -> list[dict]:
    cases = load_cases("retrieval")
    rows = []
    for mode, kwargs in CHUNK_CONFIGS:
        chunks = chunk_document(document, mode=mode, **kwargs)
        for k in KS:
            hits, ratios = [], []
            for case in cases:
                got = "\n".join(retrieve_top_k(case["query"], chunks, k=k))
                hits.append(all(e.lower() in got.lower() for e in case["expect"]))
                ratios.append(len(got) / len(document))
            rows.append({
                "mode": mode,
                "chunks": len(chunks),
                "k": k,
                "recall": mean(hits),
                # share of the document handed to the LLM; 1.0 means retrieval filtered nothing
                "context_ratio": mean(ratios),
                "misses": [c["query"] for c, h in zip(cases, hits) if not h],
            })
    return rows


def summarize(records: list[dict]) -> dict:
    ok = [r for r in records if "error" not in r]
    judged = [r["judge"]["scores"] for r in ok if "judge" in r]
    return {
        "samples": len(records),
        "errors": len(records) - len(ok),
        "judge_errors": sum("judge_error" in r for r in ok),
        "pass_rate": mean(passed(r) for r in records),
        "checks": {name: mean(r["checks"][name] for r in ok) for name in (ok[0]["checks"] if ok else [])},
        "judge": {c: mean(s[c] for s in judged) for c in (judged[0] if judged else [])},
    }


def print_summary(name: str, summary: dict, records: list[dict]) -> None:
    print(f"\n== {name}: {summary['pass_rate']:.0%} passed "
          f"({summary['samples']} samples, {summary['errors']} errors, {summary['judge_errors']} judge errors)")
    for check, rate in summary["checks"].items():
        print(f"  check {check:<16} {rate:.0%}")
    for criterion, score in summary["judge"].items():
        print(f"  judge {criterion:<16} {score:.2f} / 5")
    for r in records:
        if passed(r):
            continue
        if "error" in r:
            why = r["error"]
        else:
            failed = [c for c, v in r["checks"].items() if not v]
            low = [f"{c}={s:g}" for c, s in r.get("judge", {}).get("scores", {}).items() if s < MIN_PASSING_SCORE]
            why = ", ".join(failed + low)
        print(f"  FAIL {r['case']}#{r['sample']}: {why[:200]}")


def print_retrieval(rows: list[dict]) -> None:
    print("\n== retrieval")
    print(f"  {'mode':<10} {'chunks':>6} {'k':>2} {'recall':>7} {'context':>8}")
    for r in rows:
        print(f"  {r['mode']:<10} {r['chunks']:>6} {r['k']:>2} {r['recall']:>7.0%} {r['context_ratio']:>8.0%}")
    print("  (context = share of the document passed to the LLM; first mode is the pipeline's)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("suite", choices=["posts", "replies", "retrieval", "all"])
    parser.add_argument("--n", type=int, default=1, help="samples per case (LLM output varies run to run)")
    parser.add_argument("--model", help="generator model (default: OPENROUTER_MODEL)")
    parser.add_argument("--judge-model", help="judge model (default: EVAL_JUDGE_MODEL, else the generator default)")
    parser.add_argument("--no-judge", action="store_true", help="deterministic checks only")
    parser.add_argument("--context-file", help="read company context from a text file instead of Notion")
    args = parser.parse_args()

    suites = ["retrieval", "posts", "replies"] if args.suite == "all" else [args.suite]
    uses_llm = suites != ["retrieval"]

    judge_model = None
    if uses_llm and not args.no_judge:
        judge_model =args.judge_model or os.environ.get("EVAL_JUDGE_MODEL") or DEFAULT_MODEL

    document = ""
    if suites != ["replies"]:
        if args.context_file:
            document = Path(args.context_file).read_text(encoding="utf-8")
        else:
            from notion_fetch import get_context_text
            document = get_context_text()

    results = {
        "config": {
            "model": (args.model or DEFAULT_MODEL) if uses_llm else None,
            "judge_model": judge_model,
            "n": args.n,
            "context_sha": hashlib.sha256(document.encode()).hexdigest()[:12] if document else None,
        },
        "suites": {},
    }
    for name in suites:
        if name == "retrieval":
            rows = run_retrieval(document)
            print_retrieval(rows)
            results["suites"][name] = {"rows": rows}
            continue
        print(f"running {name} ", end="", flush=True)
        records = run_posts(document, args.n, args.model, judge_model) if name == "posts" \
            else run_replies(args.n, args.model, judge_model)
        summary = summarize(records)
        print_summary(name, summary, records)
        results["suites"][name] = {"summary": summary, "records": records}

    out = HERE / "results" / f"{datetime.now():%Y%m%d-%H%M%S}-{args.suite}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
