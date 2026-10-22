"""
Eval runner. Run from the repo root:

  python -m evals.run retrieval                 # no LLM calls
  python -m evals.run posts --n 3               # 3 samples per case
  python -m evals.run replies --model some/model --judge-model other/model
  python -m evals.run all --no-judge            # rule checks only

Nothing is posted anywhere. Full results are saved in evals/results/.
The company context comes from Notion unless --context-file is given.
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
from post_generator import NO_POST, generate_post
from retrieval import build_context, retrieve_top_k
from evals.checks import check_post, check_replies
from evals.judge import MIN_PASSING_SCORE, POST_RUBRIC, REPLY_RUBRIC, judge

HERE = Path(__file__).parent

# chunk settings to compare; the first one is what the pipeline uses
CHUNK_SETTINGS = [
    ("paragraph", {"target_chars": 500}),
    ("sentences", {"sentences_per_chunk": 4}),
    ("chars", {"size": 500}),
]
K_VALUES = [1, 3, 6]


def load_cases(name):
    path = HERE / "cases" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def error_text(e):
    return f"{type(e).__name__}: {e}"


def add_judge_scores(record, rubric, materials, judge_model):
    try:
        verdicts = []
        for material in materials:
            verdicts.append(judge(rubric, material, judge_model))
    except Exception as e:
        record["judge_error"] = error_text(e)
        return

    # average each criterion over everything that was judged
    scores = {}
    for criterion in rubric:
        scores[criterion] = mean(v["scores"][criterion] for v in verdicts)
    record["judge"] = {"scores": scores, "verdicts": verdicts}


def passed(record):
    if "error" in record:
        return False
    if not all(record["checks"].values()):
        return False
    scores = record.get("judge", {}).get("scores", {})
    return all(score >= MIN_PASSING_SCORE for score in scores.values())


def show_progress(record):
    # one character per sample: "." passed, "F" failed
    print("." if passed(record) else "F", end="", flush=True)


def run_posts(document, n, model, judge_model, records):
    for case in load_cases("posts"):
        context = build_context(document, query=case["topic"])  # same call as pipeline.write_draft
        for i in range(n):
            record = {"case": case["id"], "sample": i}
            records.append(record)
            try:
                post = generate_post(context, topic=case["topic"], max_words=case["max_words"], model=model)
            except Exception as e:
                record["error"] = error_text(e)
                continue

            record["output"] = post
            if case.get("expect_no_post"):
                record["checks"] = {"declined": post == NO_POST}
            else:
                record["checks"] = {"wrote_post": post != NO_POST}
                record["checks"].update(check_post(post, case["max_words"]))

            if judge_model and post != NO_POST:
                material = f"Company context:\n{context}\n\nRequested topic: {case['topic']}\n\nPost to score:\n{post}"
                add_judge_scores(record, POST_RUBRIC, [material], judge_model)
            show_progress(record)
    print()


def run_replies(n, model, judge_model, records):
    cases = load_cases("replies")

    # the model only sees the status fields, not our expect_review answer
    statuses = []
    for case in cases:
        status = dict(case)
        status.pop("expect_review", None)
        statuses.append(status)
    status_text = {s["id"]: s["content_text"] for s in statuses}

    for i in range(n):
        record = {"case": "batch", "sample": i}
        records.append(record)
        try:
            batch = generate_replies(statuses, model=model)
        except Exception as e:  # also catches the model returning broken JSON
            record["error"] = error_text(e)
            continue

        record["output"] = batch
        record["checks"] = check_replies(cases, batch)

        if judge_model and record["checks"]["schema_ok"]:
            materials = []
            for reply in batch["replies"]:
                if reply["in_reply_to_id"] in status_text:
                    status = status_text[reply["in_reply_to_id"]]
                    materials.append(f"Status being replied to:\n{status}\n\nReply to score:\n{reply['reply_text']}")
            if materials:
                add_judge_scores(record, REPLY_RUBRIC, materials, judge_model)
        show_progress(record)
    print()


def run_retrieval(document):
    cases = load_cases("retrieval")
    rows = []
    for mode, options in CHUNK_SETTINGS:
        chunks = chunk_document(document, mode=mode, **options)
        for k in K_VALUES:
            hits = []
            ratios = []
            misses = []
            for case in cases:
                found = "\n".join(retrieve_top_k(case["query"], chunks, k=k))
                hit = all(phrase.lower() in found.lower() for phrase in case["expect"])
                hits.append(hit)
                if not hit:
                    misses.append(case["query"])
                ratios.append(len(found) / len(document))
            rows.append({
                "mode": mode,
                "chunks": len(chunks),
                "k": k,
                "recall": mean(hits),
                # share of the page sent to the LLM; 1.0 means retrieval filtered nothing
                "context_ratio": mean(ratios),
                "misses": misses,
            })
    return rows


def summarize(records):
    ok = [r for r in records if "error" not in r]

    # collect every result per check; cases can have different checks (a declined case only has "declined")
    check_results = {}
    judge_results = {}
    judge_errors = 0
    for r in ok:
        for name, value in r["checks"].items():
            if name not in check_results:
                check_results[name] = []
            check_results[name].append(value)
        if "judge" in r:
            for name, score in r["judge"]["scores"].items():
                if name not in judge_results:
                    judge_results[name] = []
                judge_results[name].append(score)
        if "judge_error" in r:
            judge_errors += 1

    return {
        "samples": len(records),
        "errors": len(records) - len(ok),
        "judge_errors": judge_errors,
        "pass_rate": mean(passed(r) for r in records),
        "checks": {name: mean(values) for name, values in check_results.items()},
        "judge": {name: mean(scores) for name, scores in judge_results.items()},
    }


def print_summary(name, summary, records):
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
            reasons = [check for check, ok in r["checks"].items() if not ok]
            for criterion, score in r.get("judge", {}).get("scores", {}).items():
                if score < MIN_PASSING_SCORE:
                    reasons.append(f"{criterion}={score:g}")
            why = ", ".join(reasons)
        print(f"  FAIL {r['case']}#{r['sample']}: {why[:200]}")


def print_retrieval(rows):
    print("\n== retrieval")
    print(f"  {'mode':<10} {'chunks':>6} {'k':>2} {'recall':>7} {'context':>8}")
    for r in rows:
        print(f"  {r['mode']:<10} {r['chunks']:>6} {r['k']:>2} {r['recall']:>7.0%} {r['context_ratio']:>8.0%}")
    print("  (context = share of the document passed to the LLM; first mode is the pipeline's)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("suite", choices=["posts", "replies", "retrieval", "all"])
    parser.add_argument("--n", type=int, default=1, help="samples per case (LLM output varies run to run)")
    parser.add_argument("--model", help="generator model (default: OPENROUTER_MODEL)")
    parser.add_argument("--judge-model", help="judge model (default: EVAL_JUDGE_MODEL, else the generator default)")
    parser.add_argument("--no-judge", action="store_true", help="rule checks only")
    parser.add_argument("--context-file", help="read company context from a text file instead of Notion")
    args = parser.parse_args()

    if args.suite == "all":
        suites = ["retrieval", "posts", "replies"]
    else:
        suites = [args.suite]
    uses_llm = suites != ["retrieval"]

    judge_model = None
    if uses_llm and not args.no_judge:
        judge_model = args.judge_model or os.environ.get("EVAL_JUDGE_MODEL") or DEFAULT_MODEL

    # the replies suite doesn't need the company page
    document = ""
    if suites != ["replies"]:
        if args.context_file:
            document = Path(args.context_file).read_text(encoding="utf-8")
        else:
            from notion_fetch import get_context_text  # imported here so other suites don't need a Notion token
            document = get_context_text()

    page_fingerprint = None
    if document:
        # tells results from different versions of the Notion page apart
        page_fingerprint = hashlib.sha256(document.encode()).hexdigest()[:12]

    results = {
        "config": {
            "model": (args.model or DEFAULT_MODEL) if uses_llm else None,
            "judge_model": judge_model,
            "n": args.n,
            "context_sha": page_fingerprint,
        },
        "suites": {},
    }
    out_path = HERE / "results" / f"{datetime.now():%Y%m%d-%H%M%S}-{args.suite}.json"

    # save in finally, so a crash or Ctrl+C still keeps the samples already run (and paid for)
    try:
        for name in suites:
            if name == "retrieval":
                rows = run_retrieval(document)
                print_retrieval(rows)
                results["suites"]["retrieval"] = {"rows": rows}
                continue

            print(f"running {name} ", end="", flush=True)
            records = []
            results["suites"][name] = {"records": records}
            if name == "posts":
                run_posts(document, args.n, args.model, judge_model, records)
            else:
                run_replies(args.n, args.model, judge_model, records)

            summary = summarize(records)
            results["suites"][name]["summary"] = summary
            print_summary(name, summary, records)
    finally:
        out_path.parent.mkdir(exist_ok=True)
        out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nwrote {out_path.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
