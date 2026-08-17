"""
evals/run.py

Eval runner. For each golden case, generates with both arms, applies the
deterministic checkers, aggregates per-arm metrics, and writes a JSON report plus
a Markdown scorecard.

This sub-step covers the DETERMINISTIC metrics (objective, no LLM judge):
  - banned-term violation rate
  - required-disclosure coverage
  - generic-opener (anti-slop) rate
  - safe-reframing rate on adversarial traps
  - token cost per arm
LLM-judge metrics (groundedness, brand-voice) + ragas are layered in next.

Usage (from repo root, venv active):
    python -m evals.run                      # full run, both arms, all 32 cases
    python -m evals.run --limit 2            # smoke test: first 2 cases only
    python -m evals.run --arm system         # one arm only
    python -m evals.run --mock               # no API calls; canned outputs (loop test)
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from evals.checkers import check_banned_terms, check_disclosures, check_hook, check_trap
from evals.tenants import BANNED_OPENERS, TENANTS, TRAPS

DATASETS = ["meridian_wealth", "lumen_aesthetics"]
DATASET_DIR = Path("evals/datasets")
REPORT_DIR = Path("evals/reports")


# ── Data loading ─────────────────────────────────────────────────────────────
def load_cases(tenant: str | None = None, limit: int | None = None) -> list[dict]:
    cases: list[dict] = []
    for name in DATASETS:
        if tenant and name != tenant:
            continue
        path = DATASET_DIR / f"{name}.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    if limit:
        cases = cases[:limit]
    return cases


# ── Scoring (pure function — offline-testable) ───────────────────────────────
def score_generation(content: str, case: dict) -> dict:
    """Apply the deterministic checkers to one generation. No I/O, no API."""
    tcfg = TENANTS[case["tenant"]]
    banned = check_banned_terms(content, tcfg["banned"])
    disclosures = check_disclosures(content, case.get("requires_disclosures", []), tcfg["disclosures"])
    hook = check_hook(content, BANNED_OPENERS)
    result = {
        "banned_terms": banned.to_dict(),
        "disclosures": disclosures.to_dict(),
        "hook": hook.to_dict(),
    }
    if case.get("adversarial") and case.get("trap"):
        result["trap"] = check_trap(content, case["trap"], TRAPS).to_dict()
    return result


# ── Aggregation ──────────────────────────────────────────────────────────────
def aggregate(rows: list[dict], arm: str) -> dict:
    arm_rows = [r for r in rows if r["arm"] == arm and r.get("error") is None]
    n = len(arm_rows)
    if n == 0:
        return {"arm": arm, "n": 0}

    banned_viol = [0 if r["scores"]["banned_terms"]["passed"] else 1 for r in arm_rows]
    generic = [0 if r["scores"]["hook"]["passed"] else 1 for r in arm_rows]

    disc_rows = [r for r in arm_rows if r["case"].get("requires_disclosures")]
    disc_cov = [r["scores"]["disclosures"]["coverage"] for r in disc_rows]

    trap_rows = [r for r in arm_rows if "trap" in r["scores"]]
    reframed = [1 if r["scores"]["trap"]["passed"] else 0 for r in trap_rows]

    return {
        "arm": arm,
        "n": n,
        "banned_term_violation_rate": round(mean(banned_viol), 4),
        "generic_opener_rate": round(mean(generic), 4),
        "disclosure_coverage": round(mean(disc_cov), 4) if disc_cov else None,
        "disclosure_n": len(disc_rows),
        "safe_reframing_rate": round(mean(reframed), 4) if reframed else None,
        "adversarial_n": len(trap_rows),
        "total_cost_usd": round(sum(r["cost_usd"] for r in arm_rows), 6),
        "avg_completion_tokens": round(mean(r["completion_tokens"] for r in arm_rows), 1),
        "errors": sum(1 for r in rows if r["arm"] == arm and r.get("error")),
    }


# ── Mock generation (no API) ─────────────────────────────────────────────────
def _mock_generation(arm: str, case: dict):
    """Canned outputs so the full scoring loop is verifiable without spending."""
    from evals.arms import Generation

    if arm == "baseline":
        # Deliberately bad: generic opener + takes adversarial bait + no disclosures.
        text = "In today's world, this is an amazing, guaranteed, risk-free opportunity you can't miss!"
        if case["tenant"] == "lumen_aesthetics":
            text = "In today's world, our treatments are 100% safe with no side effects and permanent results."
    else:
        # Deliberately good: specific hook, disclosures present, no banned terms.
        if case["tenant"] == "meridian_wealth":
            text = ("Meridian charges one all-in advisory fee in basis points, disclosed before onboarding. "
                    "Past performance is not a reliable indicator of future results, and the value of "
                    "investments can fall as well as rise. This is marketing, not personal advice. "
                    "Book a portfolio review to discuss suitability.")
        else:
            text = ("A qualified practitioner assesses suitability at an individual consultation. Results vary "
                    "between individuals and are temporary; possible side effects include temporary bruising "
                    "and swelling. Book a consultation to discuss whether this is right for you.")
    return Generation(
        arm=arm, case_id=case["id"], tenant=case["tenant"], content_type=case["content_type"],
        content=text, model="mock", prompt_tokens=0, completion_tokens=len(text.split()),
        cost_usd=0.0, retrieved_k=(0 if arm == "baseline" else 3),
    )


# ── Runner ───────────────────────────────────────────────────────────────────
def run(arms: list[str], cases: list[dict], mock: bool) -> dict:
    llm = None
    if not mock:
        from evals.llm import EvalLLM
        llm = EvalLLM()

    rows: list[dict] = []
    for case in cases:
        for arm in arms:
            if mock:
                gen = _mock_generation(arm, case)
            else:
                from evals.arms import generate
                gen = generate(arm, case, llm)
            row = {
                "arm": arm, "case_id": case["id"], "tenant": case["tenant"],
                "content_type": case["content_type"], "case": case,
                "content": gen.content, "error": gen.error,
                "prompt_tokens": gen.prompt_tokens, "completion_tokens": gen.completion_tokens,
                "cost_usd": gen.cost_usd, "retrieved_k": gen.retrieved_k,
                "scores": None if gen.error else score_generation(gen.content, case),
            }
            rows.append(row)
            status = "ERR" if gen.error else "ok"
            print(f"  [{status}] {arm:<8} {case['id']:<14} k={gen.retrieved_k}")

    summary = {arm: aggregate(rows, arm) for arm in arms}
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_cases": len(cases),
        "arms": arms,
        "mock": mock,
        "summary": summary,
        "rows": rows,
    }


def render_scorecard(report: dict) -> str:
    s = report["summary"]
    lines = ["# Eval Scorecard", "", f"_Generated {report['generated_at']} · "
             f"{report['n_cases']} cases · mock={report['mock']}_", ""]
    metrics = [
        ("Banned-term violation rate", "banned_term_violation_rate", "lower"),
        ("Generic-opener rate", "generic_opener_rate", "lower"),
        ("Disclosure coverage", "disclosure_coverage", "higher"),
        ("Safe-reframing rate (adversarial)", "safe_reframing_rate", "higher"),
        ("Total cost (USD)", "total_cost_usd", "-"),
        ("Avg completion tokens", "avg_completion_tokens", "-"),
    ]
    arms = report["arms"]
    header = "| Metric | " + " | ".join(arms) + " | better |"
    sep = "|" + "---|" * (len(arms) + 2)
    lines += [header, sep]
    for label, key, better in metrics:
        cells = []
        for arm in arms:
            v = s.get(arm, {}).get(key)
            cells.append("—" if v is None else str(v))
        lines.append(f"| {label} | " + " | ".join(cells) + f" | {better} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the content eval harness.")
    ap.add_argument("--arm", choices=["baseline", "system"], help="Run only one arm.")
    ap.add_argument("--tenant", choices=DATASETS, help="Run only one tenant.")
    ap.add_argument("--limit", type=int, help="Only the first N cases.")
    ap.add_argument("--mock", action="store_true", help="No API calls; canned outputs.")
    ap.add_argument("--out", default=None, help="Report path prefix (default: timestamped).")
    args = ap.parse_args()

    arms = [args.arm] if args.arm else ["baseline", "system"]
    cases = load_cases(tenant=args.tenant, limit=args.limit)
    print(f"Running {len(cases)} cases x {len(arms)} arm(s){' [MOCK]' if args.mock else ''} ...")

    report = run(arms, cases, mock=args.mock)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    prefix = args.out or str(REPORT_DIR / f"eval_{'mock_' if args.mock else ''}{stamp}")
    Path(prefix + ".json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    scorecard = render_scorecard(report)
    Path(prefix + ".md").write_text(scorecard, encoding="utf-8")

    print("\n" + scorecard)
    print(f"Wrote {prefix}.json and {prefix}.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
