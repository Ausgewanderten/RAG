import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class SourceStateTests(unittest.TestCase):
    def _settings(self, base: Path):
        from raggg.config import Settings

        return Settings(
            project_root=base,
            waveda_help_root=base / "helpHtml",
            obsidian_vault_root=base / "vault",
            extra_markdown_roots=[base / "knowledge_sources"],
            data_dir=base / "data",
            embedding_model="local",
            llm_base_url="",
            llm_api_key="",
            llm_model="",
        )

    def test_source_state_detects_changes_after_snapshot_is_written(self):
        from raggg.pipeline.source_state import has_source_changes, write_source_state

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "helpHtml").mkdir()
            (base / "vault").mkdir()
            (base / "knowledge_sources").mkdir()
            (base / "helpHtml" / "Wave_Port.html").write_text("<html>波端口</html>", encoding="utf-8")
            (base / "vault" / "Maxwell.md").write_text("# Maxwell", encoding="utf-8")
            settings = self._settings(base)

            self.assertTrue(has_source_changes(settings))
            snapshot = write_source_state(settings)

            self.assertFalse(has_source_changes(settings))
            self.assertEqual(snapshot.file_count, 2)

            (base / "knowledge_sources" / "ports.md").write_text("# 端口资料", encoding="utf-8")

            self.assertTrue(has_source_changes(settings))

    def test_builder_writes_source_snapshot_after_successful_build(self):
        from raggg.pipeline.builder import build_knowledge_base
        from raggg.pipeline.source_state import has_source_changes

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "helpHtml").mkdir()
            (base / "vault").mkdir()
            (base / "knowledge_sources").mkdir()
            (base / "helpHtml" / "Wave_Port.html").write_text(
                "<html><head><title>波端口</title></head><body>波端口用于设置激励。</body></html>",
                encoding="utf-8",
            )
            settings = self._settings(base)

            build_knowledge_base(settings)

            self.assertTrue((base / "data" / "source_state.json").exists())
            self.assertFalse(has_source_changes(settings))


if __name__ == "__main__":
    unittest.main()
