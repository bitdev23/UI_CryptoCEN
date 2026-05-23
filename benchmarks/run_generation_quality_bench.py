#!/usr/bin/env python3
"""Run a lightweight quality benchmark against generated post outputs.

Usage:
  python benchmarks/run_generation_quality_bench.py \
    --suite benchmarks/generation_quality_suite.sample.json \
    --responses benchmarks/results/latest_outputs.json
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)
NUMBER_RE = re.compile(r"(?<!\w)(\d+(?:\.\d+)?)(?!\w)")


@dataclass
class CaseResult:
    case_id: str
    passed: bool
    score: float
    checks: Dict[str, Any]


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _pick_text(record: Dict[str, Any]) -> str:
    """Extract generated text from common payload shapes."""
    candidates = [
        record.get("content"),
        record.get("text"),
        record.get("post"),
        record.get("generated_text"),
        record.get("generated_post"),
        record.get("output"),
        record.get("response"),
        record.get("text_preview"),
    ]
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value
    return ""


def normalize_responses(raw: Any) -> Dict[str, str]:
    """Normalize real generation outputs into case_id -> generated text mapping.

    Supported input formats:
      1) {"case_id": "generated text", ...}
      2) [{"case_id": "...", "content": "..."}, ...]
      3) {"results": [{"id": "...", "text": "..."}, ...]}
      4) {"cases": [{"id": "...", "response": {"content": "..."}}, ...]}
    """
    if isinstance(raw, dict) and all(isinstance(v, str) for v in raw.values()):
        return {str(k): str(v) for k, v in raw.items()}

    records: List[Dict[str, Any]] = []
    if isinstance(raw, list):
        records = [r for r in raw if isinstance(r, dict)]
    elif isinstance(raw, dict):
        if isinstance(raw.get("results"), list):
            records = [r for r in raw.get("results", []) if isinstance(r, dict)]
        elif isinstance(raw.get("cases"), list):
            records = [r for r in raw.get("cases", []) if isinstance(r, dict)]

    normalized: Dict[str, str] = {}
    for rec in records:
        case_id = str(rec.get("case_id") or rec.get("id") or rec.get("prompt_id") or "").strip()
        if not case_id:
            continue

        text = _pick_text(rec)
        if not text and isinstance(rec.get("response"), dict):
            text = _pick_text(rec.get("response", {}))

        normalized[case_id] = text

    return normalized


def _word_count(text: str) -> int:
    return len(WORD_RE.findall(text or ""))


def _numbers(text: str) -> List[float]:
    values: List[float] = []
    for match in NUMBER_RE.findall(text or ""):
        try:
            values.append(float(match))
        except ValueError:
            continue
    return values


def evaluate_case(case: Dict[str, Any], output_text: str) -> CaseResult:
    exp = case.get("expectations") or {}
    output_lc = (output_text or "").lower()

    must_include = [str(v).strip().lower() for v in exp.get("must_include", []) if str(v).strip()]
    must_not_include = [str(v).strip().lower() for v in exp.get("must_not_include", []) if str(v).strip()]
    min_words = int(exp.get("min_word_count", 0) or 0)
    expected_numbers = [float(v) for v in exp.get("expected_numbers", [])]

    include_hits = [phrase for phrase in must_include if phrase in output_lc]
    include_ok = len(include_hits) == len(must_include)

    forbidden_hits = [phrase for phrase in must_not_include if phrase in output_lc]
    forbidden_ok = len(forbidden_hits) == 0

    words = _word_count(output_text)
    words_ok = words >= min_words

    found_numbers = _numbers(output_text)
    expected_set = set(expected_numbers)
    found_set = set(found_numbers)
    numeric_ok = expected_set.issubset(found_set) if expected_numbers else True

    checks = {
        "must_include": {
            "required": must_include,
            "matched": include_hits,
            "ok": include_ok,
        },
        "must_not_include": {
            "required": must_not_include,
            "violations": forbidden_hits,
            "ok": forbidden_ok,
        },
        "min_word_count": {
            "required": min_words,
            "actual": words,
            "ok": words_ok,
        },
        "expected_numbers": {
            "required": expected_numbers,
            "found": found_numbers,
            "ok": numeric_ok,
        },
    }

    check_values = [include_ok, forbidden_ok, words_ok, numeric_ok]
    score = round((sum(1 for v in check_values if v) / len(check_values)) * 100.0, 1)
    passed = all(check_values)

    return CaseResult(case_id=str(case.get("id", "unknown")), passed=passed, score=score, checks=checks)


def run_suite(suite: Dict[str, Any], responses: Dict[str, str]) -> Tuple[List[CaseResult], Dict[str, Any]]:
    results: List[CaseResult] = []
    for case in suite.get("cases", []):
        case_id = str(case.get("id", "")).strip()
        output_text = str(responses.get(case_id, ""))
        results.append(evaluate_case(case, output_text))

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    avg_score = round(sum(r.score for r in results) / total, 1) if total else 0.0

    summary = {
        "suite_name": suite.get("suite_name", "unnamed_suite"),
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "pass_rate": round((passed / total) * 100.0, 1) if total else 0.0,
        "avg_score": avg_score,
    }
    return results, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a generation quality benchmark suite")
    parser.add_argument("--suite", required=True, help="Path to benchmark suite JSON")
    parser.add_argument("--responses", required=True, help="Path to JSON mapping case_id -> generated text (or raw generation output list/object)")
    parser.add_argument("--output", default="benchmarks/results/generation_quality_report.json", help="Report output path")
    parser.add_argument("--min-pass-rate", type=float, default=0.0, help="Fail with non-zero exit code if pass_rate is below this threshold")
    args = parser.parse_args()

    suite_path = Path(args.suite)
    responses_path = Path(args.responses)
    output_path = Path(args.output)

    suite = _load_json(suite_path)
    responses_raw = _load_json(responses_path)
    responses = normalize_responses(responses_raw)
    results, summary = run_suite(suite, responses)

    report = {
        "summary": summary,
        "results": [
            {
                "case_id": r.case_id,
                "passed": r.passed,
                "score": r.score,
                "checks": r.checks,
            }
            for r in results
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(json.dumps(summary, indent=2))
    print(f"Saved report to {output_path}")

    if summary.get("pass_rate", 0.0) < float(args.min_pass_rate):
        raise SystemExit(
            f"Benchmark failed: pass_rate={summary.get('pass_rate', 0.0)} < min_pass_rate={args.min_pass_rate}"
        )


if __name__ == "__main__":
    main()
