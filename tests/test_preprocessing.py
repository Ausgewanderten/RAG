import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class PreprocessingTests(unittest.TestCase):
    def test_clean_text_removes_comments_and_collapses_whitespace(self):
        from raggg.preprocessing.cleaner import clean_text

        raw = "---\ntype: note\n---\n提示：所有绿色注释下面的区域是替换的部分\n\n波端口   用于\n\n设置激励。"

        self.assertEqual(clean_text(raw), "波端口 用于\n设置激励。")

    def test_chunker_preserves_formula_and_metadata(self):
        from raggg.models import Document
        from raggg.preprocessing.chunker import chunk_document

        doc = Document(
            source_type="obsidian_note",
            source_path=Path(r"D:\notes\Maxwell.md"),
            relative_path="Maxwell.md",
            title="Maxwell 方程组",
            text="# Maxwell 方程组\n\n$$\n\\nabla \\cdot D = \\rho\n$$\n\n它描述电磁场。",
            links=["边界条件"],
            images=[],
            metadata={"domain": "multiphysics", "content_type": "note", "has_formula": True},
        )

        chunks = chunk_document(doc, target_chars=40)

        self.assertEqual(len(chunks), 1)
        self.assertIn("\\nabla \\cdot D", chunks[0].content)
        self.assertEqual(chunks[0].source_type, "obsidian_note")
        self.assertEqual(chunks[0].metadata["has_formula"], True)
        self.assertTrue(chunks[0].id.startswith("obsidian_note:Maxwell.md:"))

    def test_chunk_formula_metadata_is_based_on_chunk_content(self):
        from raggg.models import Document
        from raggg.preprocessing.chunker import chunk_document

        doc = Document(
            source_type="obsidian_note",
            source_path=Path(r"D:\notes\mixed.md"),
            relative_path="mixed.md",
            title="混合页面",
            text="# 混合页面\n\n学习目标和导航。\n\n## 公式\n\n$$\\nabla \\cdot D = \\rho$$",
            metadata={"domain": "multiphysics", "content_type": "note", "has_formula": True},
        )

        chunks = chunk_document(doc, target_chars=10)

        self.assertFalse(chunks[0].metadata["has_formula"])
        self.assertTrue(chunks[-1].metadata["has_formula"])

    def test_chunk_ids_are_stable(self):
        from raggg.models import Document
        from raggg.preprocessing.chunker import chunk_document

        doc = Document(
            source_type="waveda_help",
            source_path=Path(r"D:\help\Boundary.html"),
            relative_path="EM_Project/Boundary.html",
            title="边界",
            text="边界条件包括 PML、阻抗边界和开放边界。",
            metadata={"domain": "waveda", "content_type": "help_page"},
        )

        first = chunk_document(doc)[0].id
        second = chunk_document(doc)[0].id

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
