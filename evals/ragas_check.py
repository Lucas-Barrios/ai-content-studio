"""
evals/ragas_check.py

Optional independent cross-check: runs ragas Faithfulness on the system-arm
generations from a saved eval report, to sit beside our own groundedness judge.

Why a separate, opt-in module (not part of run.py):
  ragas pulls a heavy, version-sensitive dependency tree (langchain et al.). Keeping
  it isolated means a ragas install/version problem can never break the core harness.
  Pinned known-good set (see requirements-ragas.txt):
    ragas==0.2.10, langchain-community>=0.3,<0.4, langchain-openai

Faithfulness = fraction of the answer's claims that are supported by the retrieved
contexts — the same construct as our groundedness judge, computed by an independent
library, so agreement between the two is evidence the number is real.

Usage (from repo root, venv active, OPENAI_API_KEY set):
    pip install -r requirements-ragas.txt
    python -m evals.ragas_check                     # newest report in evals/reports
    python -m evals.ragas_check --report evals/reports/eval_20260817_203547.json
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPORT_DIR = Path("evals/reports")


def _latest_report() -> str:
    candidates = sorted(glob.glob(str(REPORT_DIR / "eval_*.json")))
    candidates = [c for c in candidates if "mock" not in c and "_ragas" not in c]
    if not candidates:
        raise SystemExit("No non-mock report found in evals/reports. Run `python -m evals.run` first.")
    return candidates[-1]


def main() -> int:
    ap = argparse.ArgumentParser(description="Ragas faithfulness cross-check on a saved report.")
    ap.add_argument("--report", default=None, help="Path to an eval_*.json report (default: newest).")
    ap.add_argument("--model", default=None, help="Judge model for ragas (default: JUDGE_MODEL or gpt-4o).")
    args = ap.parse_args()

    report_path = args.report or _latest_report()
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))

    # Build ragas samples from system-arm rows that have retrieved context.
    rows = [
        r for r in report["rows"]
        if r["arm"] == "system" and not r.get("error") and r.get("retrieved_context", "").strip()
    ]
    if not rows:
        raise SystemExit("No system rows with retrieved context in this report.")

    # Import ragas lazily so a missing/broken install fails loudly here, not on import.
    try:
        from langchain_openai import ChatOpenAI
        from ragas import EvaluationDataset, SingleTurnSample, evaluate
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import Faithfulness
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            f"ragas import failed ({exc}). Install the pinned set:\n"
            f"  pip install -r requirements-ragas.txt"
        )

    samples = [
        SingleTurnSample(
            user_input=r["case"]["topic"],
            response=r["content"],
            retrieved_contexts=[r["retrieved_context"]],
        )
        for r in rows
    ]
    dataset = EvaluationDataset(samples=samples)

    model = args.model or os.getenv("JUDGE_MODEL", "gpt-4o")
    llm = LangchainLLMWrapper(ChatOpenAI(model=model, temperature=0))
    print(f"Running ragas Faithfulness on {len(samples)} system generations with {model} ...")

    result = evaluate(dataset=dataset, metrics=[Faithfulness()], llm=llm)
    df = result.to_pandas()

    scores = df["faithfulness"].tolist()
    per_case = [
        {"case_id": r["case_id"], "faithfulness": (None if s != s else round(float(s), 4))}
        for r, s in zip(rows, scores)
    ]
    valid = [s for s in scores if s == s]  # drop NaN
    mean_faith = round(sum(valid) / len(valid), 4) if valid else None

    our_ground = report["summary"].get("system", {}).get("groundedness_score")

    out = {
        "report": report_path,
        "model": model,
        "n": len(rows),
        "ragas_faithfulness_mean": mean_faith,
        "our_groundedness_mean": our_ground,
        "per_case": per_case,
    }
    out_path = report_path.replace(".json", "_ragas.json")
    Path(out_path).write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"\nragas faithfulness (independent):  {mean_faith}")
    print(f"our groundedness judge:            {our_ground}")
    if mean_faith is not None and our_ground is not None:
        print(f"agreement (|delta|):               {round(abs(mean_faith - our_ground), 4)}")
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
