import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class ConfigTests(unittest.TestCase):
    def test_default_paths_live_under_project(self):
        from raggg.config import Settings

        settings = Settings.from_env({})

        self.assertEqual(settings.project_root, ROOT)
        self.assertEqual(settings.data_dir, ROOT / "data")
        self.assertEqual(
            settings.waveda_help_root,
            Path(r"D:\Program Files (x86)\documentation\helpHtml"),
        )
        self.assertEqual(
            settings.obsidian_vault_root,
            Path(r"D:\暑期实践\多物理场仿真知识库"),
        )

    def test_environment_overrides_are_supported(self):
        from raggg.config import Settings

        env = {
            "WAVEDA_HELP_ROOT": r"C:\docs\waveda",
            "OBSIDIAN_VAULT_ROOT": r"C:\notes",
            "RAG_DATA_DIR": r"C:\rag-data",
            "RAG_LLM_BASE_URL": "https://example.test/v1",
            "RAG_LLM_API_KEY": "secret",
            "RAG_LLM_MODEL": "test-model",
        }

        settings = Settings.from_env(env)

        self.assertEqual(settings.waveda_help_root, Path(r"C:\docs\waveda"))
        self.assertEqual(settings.obsidian_vault_root, Path(r"C:\notes"))
        self.assertEqual(settings.data_dir, Path(r"C:\rag-data"))
        self.assertEqual(settings.llm_base_url, "https://example.test/v1")
        self.assertEqual(settings.llm_api_key, "secret")
        self.assertEqual(settings.llm_model, "test-model")

    def test_dotenv_loader_ignores_missing_files(self):
        from raggg.config import load_dotenv_file

        missing = ROOT / "missing.env"

        self.assertEqual(load_dotenv_file(missing), {})

    def test_portable_root_resolves_relative_paths(self):
        from raggg.config import Settings

        portable_root = ROOT / "portable-sample"
        settings = Settings.from_env(
            {
                "RAGGG_PORTABLE_ROOT": str(portable_root),
                "RAG_DATA_DIR": "data",
                "WAVEDA_HELP_ROOT": "sources/helpHtml",
                "OBSIDIAN_VAULT_ROOT": "sources/vault",
            }
        )

        self.assertEqual(settings.project_root, portable_root)
        self.assertEqual(settings.data_dir, portable_root / "data")
        self.assertEqual(settings.waveda_help_root, portable_root / "sources" / "helpHtml")
        self.assertEqual(settings.obsidian_vault_root, portable_root / "sources" / "vault")

    def test_extra_markdown_roots_support_multiple_paths(self):
        from raggg.config import Settings

        portable_root = ROOT / "portable-sample"
        settings = Settings.from_env(
            {
                "RAGGG_PORTABLE_ROOT": str(portable_root),
                "RAG_EXTRA_MARKDOWN_ROOTS": r"sources\waveda_agent_kb;C:\shared\extra_notes",
            }
        )

        self.assertEqual(
            settings.extra_markdown_roots,
            [portable_root / "sources" / "waveda_agent_kb", Path(r"C:\shared\extra_notes")],
        )


if __name__ == "__main__":
    unittest.main()
