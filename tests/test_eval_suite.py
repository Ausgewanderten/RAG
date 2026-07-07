import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))


class WavedaEvalSuiteTests(unittest.TestCase):
    def test_eval_fixture_has_required_shape(self):
        cases = json.loads((ROOT / "tests" / "fixtures" / "waveda_eval_cases.json").read_text(encoding="utf-8"))

        self.assertGreaterEqual(len(cases), 30)
        ids = [case["id"] for case in cases]
        self.assertEqual(len(ids), len(set(ids)))
        for case in cases:
            self.assertIsInstance(case["question"], str)
            self.assertTrue(case["question"])
            self.assertIsInstance(case["expected_source_contains"], list)
            self.assertTrue(case["expected_source_contains"])
            self.assertIsInstance(case["required_terms"], list)
            self.assertIn("引用来源", case["required_terms"])

    def test_eval_runner_can_score_cases_without_llm(self):
        from scripts.evaluate_waveda_qa import load_cases, run_evaluation

        index_dir = ROOT / "data" / "index"
        if not (index_dir / "chunks.json").exists():
            self.skipTest("real index has not been built")

        cases = load_cases(ROOT / "tests" / "fixtures" / "waveda_eval_cases.json")
        results = run_evaluation(cases[:5], data_dir=ROOT / "data", top_k=6)

        self.assertEqual(len(results), 5)
        self.assertTrue(all(result.passed for result in results), [result.to_line() for result in results])


if __name__ == "__main__":
    unittest.main()
