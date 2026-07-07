import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class DesktopImportTests(unittest.TestCase):
    def test_desktop_application_class_is_importable(self):
        from raggg.desktop.main_window import RAGDesktopApp

        self.assertTrue(hasattr(RAGDesktopApp, "run"))

    def test_markdown_answer_is_rendered_without_raw_stars(self):
        from raggg.desktop.main_window import markdown_to_html

        rendered = markdown_to_html("1. **创建平面波源**：右击激励源\n- **方向**：设置 k 向量")

        self.assertIn("<strong>创建平面波源</strong>", rendered)
        self.assertIn("<strong>方向</strong>", rendered)
        self.assertNotIn("**", rendered)
        self.assertIn("<ol>", rendered)
        self.assertIn("<ul>", rendered)

    def test_latex_formula_is_rendered_readably(self):
        from raggg.desktop.main_window import markdown_to_html

        rendered = markdown_to_html(r"公式 \(\frac{\partial u}{\partial n}+jku=0\) 用于吸收边界。")

        self.assertIn("(∂u)/(∂n)+jku=0", rendered)
        self.assertNotIn(r"\frac", rendered)
        self.assertNotIn(r"\partial", rendered)
        self.assertNotIn(r"\(", rendered)

    def test_integral_latex_keeps_formula_structure(self):
        from raggg.desktop.main_window import markdown_to_html

        rendered = markdown_to_html(
            r"电场高斯定律：\(\oiint_S \mathbf{D}\cdot d\mathbf{S} = \iiint_V \rho_f\,dV\)"
        )

        self.assertIn("∯<sub>S</sub>", rendered)
        self.assertIn("<span style=", rendered)
        self.assertIn("D · dS", rendered)
        self.assertIn("∭<sub>V</sub>", rendered)
        self.assertIn("ρ<sub>f</sub>", rendered)
        self.assertNotIn("oiint", rendered)
        self.assertNotIn("iiint", rendered)


if __name__ == "__main__":
    unittest.main()
