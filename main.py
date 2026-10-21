# Run one tweet file through the agent, or through the baseline with --baseline.


import argparse
import json
import time
from pathlib import Path

from src.config import DATA_PROCESSED, ONTOLOGY_PATH, SUMMARY_SENTENCES, USER_PROMPTS, load_documents
from src.graph.graph import build_baseline_graph, build_graph, initial_state


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data",
        type=Path,
        required=True,
        help="DivSumm input_docs/*.txt file, or a JSON list of tweets",
    )
    parser.add_argument("--prompt", choices=sorted(USER_PROMPTS), required=True)
    parser.add_argument("--topic", help="Topic name. Defaults to the topic on the first tweet.")
    parser.add_argument("--k", type=int, default=SUMMARY_SENTENCES, help="Sentences in the summary")
    parser.add_argument("--runs", type=int, default=1, help="Repeated runs, for generation variability")
    parser.add_argument("--baseline", action="store_true", help="One-shot LLM, no ontology")
    parser.add_argument("--save", action="store_true", help="Write each run under data/processed")
    return parser.parse_args()


def main():
    args = parse_args()
    documents = load_documents(args.data)
    topic = args.topic or documents[0]["topic"]
    if not topic:
        raise SystemExit("Pass --topic or include a topic field on the tweets.")
    prompt = USER_PROMPTS[args.prompt]
    mode = "baseline" if args.baseline else "agent"
    graph = build_baseline_graph() if args.baseline else build_graph()

    if mode == "agent" and not ONTOLOGY_PATH.is_file():
        print(f"Ontology file missing: {ONTOLOGY_PATH}")
        print("Export the Protégé ontology to that path. Queries will be marked as errors until then.")

    for run_index in range(1, args.runs + 1):
        state = initial_state(
            documents=documents,
            user_prompt=prompt,
            topic=topic,
            prompt_id=args.prompt,
            k=args.k,
            mode=mode,
        )
        started = time.perf_counter()
        result = graph.invoke(state)
        elapsed = time.perf_counter() - started
        _print_run(run_index, result, elapsed)
        if args.save:
            _save_run(args, run_index, result, elapsed)

def _print_run(run_index, result, elapsed):
    print(f"\n=== run {run_index} ({result['mode']}) {elapsed:.2f}s ===")
    print(result["summary"])
    if result["mode"] == "agent":
        print(f"passed: {result['passed']}  revisions: {result['revision']}")
        for verdict in result.get("claim_evaluations") or []:
            claim = verdict["claim"]
            print(
                f"claim {verdict['status']}: {claim.get('subject')} {claim.get('predicate')} "
                f"{claim.get('object')} [{claim.get('scope')}]"
            )
        if result["issues"]:
            print("issues:")
            for issue in result["issues"]:
                print(f"- [{issue['kind']}] {issue['message']}")
        if result["issues"] and result["revision"] >= result["max_revisions"]:
            print("Contradictions remain after the rewrite limit. Validation did not succeed.")
        errors = [item for item in result["query_results"] if item["status"] == "error"]
        for item in errors:
            print(f"query error {item['query_id']}: {item['detail']}")

def _save_run(args, run_index, result, elapsed):
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    mode = "baseline" if args.baseline else "agent"
    destination = DATA_PROCESSED / f"{result['topic']}_{args.prompt}_{mode}_run{run_index}.json"
    payload = {
        "topic": result["topic"],
        "prompt_id": result["prompt_id"],
        "mode": result["mode"],
        "summary": result["summary"],
        "issues": result["issues"],
        "claims": result.get("claims") or [],
        "mapped_claims": result.get("mapped_claims") or [],
        "claim_evaluations": result.get("claim_evaluations") or [],
        "revision": result["revision"],
        "passed": result["passed"] if result["mode"] == "agent" else None,
        "trace": result["trace"],
        "elapsed_seconds": round(elapsed, 3),
        "query_results": result["query_results"],
    }
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {destination}")


if __name__ == "__main__":
    main()
