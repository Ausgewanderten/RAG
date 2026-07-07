from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from raggg.generation.prompt_builder import build_local_answer
from raggg.indexing.vector_store import VectorStore
from raggg.retrieval.retriever import Retriever


@dataclass(frozen=True)
class EvalCase:
    id: str
    question: str
    expected_source_contains: list[str]
    required_terms: list[str]


@dataclass(frozen=True)
class EvalResult:
    case_id: str
    passed: bool
    source_ok: bool
    answer_ok: bool
    top_sources: list[str]
    missing_terms: list[str]

    def to_line(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        details = ", ".join(self.top_sources[:3])
        missing = "" if not self.missing_terms else f" | missing={self.missing_terms}"
        return f"{status} {self.case_id} | sources={details}{missing}"


def load_cases(path: Path) -> list[EvalCase]:
    raw_cases = json.loads(path.read_text(encoding="utf-8"))
    cases: list[EvalCase] = []
    for item in raw_cases:
        cases.append(
            EvalCase(
                id=str(item["id"]),
                question=str(item["question"]),
                expected_source_contains=[str(value) for value in item["expected_source_contains"]],
                required_terms=[str(value) for value in item["required_terms"]],
            )
        )
    return cases


def _contains_any_source(top_sources: list[str], expected: list[str]) -> bool:
    haystack = "\n".join(top_sources).lower()
    return any(needle.lower() in haystack for needle in expected)


def _case_from_mapping(item: EvalCase | Mapping[str, Any]) -> EvalCase:
    if isinstance(item, EvalCase):
        return item
    return EvalCase(
        id=str(item["id"]),
        question=str(item["question"]),
        expected_source_contains=[str(value) for value in item["expected_source_contains"]],
        required_terms=[str(value) for value in item["required_terms"]],
    )


def run_evaluation(
    cases: list[EvalCase] | list[Mapping[str, Any]],
    data_dir: Path,
    top_k: int = 6,
) -> list[EvalResult]:
    store = VectorStore.load(data_dir / "index")
    retriever = Retriever(store)
    results: list[EvalResult] = []
    for raw_case in cases:
        case = _case_from_mapping(raw_case)
        sources = retriever.search(case.question, top_k=top_k)
        answer = build_local_answer(case.question, sources)
        top_sources = [
            f"{source.chunk.title} | {source.chunk.source_type} | {source.chunk.relative_path}"
            for source in sources
        ]
        missing_terms = [term for term in case.required_terms if term not in answer]
        source_ok = _contains_any_source(top_sources, case.expected_source_contains)
        answer_ok = not missing_terms
        results.append(
            EvalResult(
                case_id=case.id,
                passed=source_ok and answer_ok,
                source_ok=source_ok,
                answer_ok=answer_ok,
                top_sources=top_sources,
                missing_terms=missing_terms,
            )
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate local WavEDA RAG retrieval and answer templates.")
    parser.add_argument(
        "--cases",
        type=Path,
        default=ROOT / "tests" / "fixtures" / "waveda_eval_cases.json",
        help="Path to the evaluation case JSON file.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=ROOT / "data",
        help="Path to the RAG data directory containing index/chunks.json and vectors.npy.",
    )
    parser.add_argument("--top-k", type=int, default=6)
    args = parser.parse_args()

    cases = load_cases(args.cases)
    results = run_evaluation(cases, data_dir=args.data_dir, top_k=args.top_k)
    for result in results:
        print(result.to_line())
    passed = sum(1 for result in results if result.passed)
    total = len(results)
    print(f"SUMMARY passed={passed} failed={total - passed} total={total}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
