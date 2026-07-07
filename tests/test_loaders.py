import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class LoaderTests(unittest.TestCase):
    def test_html_loader_extracts_title_text_links_and_images(self):
        from raggg.loaders.html_loader import load_html_document

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "Modeling" / "Stimulate" / "Wave_Port.html"
            page.parent.mkdir(parents=True)
            page.write_text(
                """<!DOCTYPE html>
                <html><head><title>波端口</title></head>
                <body>
                  <header><h1>WavEDA</h1></header>
                  <h1>波端口</h1>
                  <p>波端口用于设置端口激励。</p>
                  <a href="../EM_Project/EM_Results.html">电磁结果</a>
                  <img src="./images/Wave_Port_1.png" alt="端口设置窗口">
                </body></html>""",
                encoding="utf-8",
            )

            doc = load_html_document(page, root)

        self.assertEqual(doc.source_type, "waveda_help")
        self.assertEqual(doc.relative_path, "Modeling/Stimulate/Wave_Port.html")
        self.assertEqual(doc.title, "波端口")
        self.assertIn("波端口用于设置端口激励", doc.text)
        self.assertIn("../EM_Project/EM_Results.html", doc.links)
        self.assertIn("端口设置窗口", doc.images)

    def test_markdown_loader_extracts_title_wikilinks_and_formula(self):
        from raggg.loaders.markdown_loader import load_markdown_document

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = root / "01-基础概念" / "Maxwell方程组是什么.md"
            note.parent.mkdir(parents=True)
            note.write_text(
                """# Maxwell 方程组是什么

关联：[[边界条件]]

$$
\\nabla \\times E = -\\frac{\\partial B}{\\partial t}
$$

它描述电场和磁场的耦合。
""",
                encoding="utf-8",
            )

            doc = load_markdown_document(note, root)

        self.assertEqual(doc.source_type, "obsidian_note")
        self.assertEqual(doc.relative_path, "01-基础概念/Maxwell方程组是什么.md")
        self.assertEqual(doc.title, "Maxwell 方程组是什么")
        self.assertIn("[[边界条件]]", doc.text)
        self.assertIn("边界条件", doc.links)
        self.assertTrue(doc.metadata["has_formula"])
        self.assertTrue(doc.metadata["has_wikilink"])


if __name__ == "__main__":
    unittest.main()
