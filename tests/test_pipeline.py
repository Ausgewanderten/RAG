import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class PipelineTests(unittest.TestCase):
    def test_builder_creates_index_from_sample_roots(self):
        from raggg.config import Settings
        from raggg.pipeline.builder import build_knowledge_base

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            help_root = base / "helpHtml"
            note_root = base / "vault"
            data_dir = base / "data"
            help_root.mkdir()
            note_root.mkdir()
            (help_root / "Wave_Port.html").write_text(
                "<html><head><title>波端口</title></head><body><p>波端口用于设置激励。</p></body></html>",
                encoding="utf-8",
            )
            (note_root / "Maxwell.md").write_text(
                "# Maxwell 方程组\n\n$$\\nabla \\cdot D = \\rho$$",
                encoding="utf-8",
            )
            settings = Settings(
                project_root=base,
                waveda_help_root=help_root,
                obsidian_vault_root=note_root,
                data_dir=data_dir,
                embedding_model="local",
                llm_base_url="",
                llm_api_key="",
                llm_model="",
            )

            report = build_knowledge_base(settings)

            self.assertEqual(report.document_count, 2)
            self.assertGreaterEqual(report.chunk_count, 2)
            self.assertTrue((data_dir / "processed_chunks.json").exists())
            self.assertTrue((data_dir / "index" / "chunks.json").exists())
            self.assertTrue((data_dir / "index" / "vectors.npy").exists())

    def test_builder_includes_extra_markdown_roots(self):
        from raggg.config import Settings
        from raggg.pipeline.builder import build_knowledge_base

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            help_root = base / "helpHtml"
            note_root = base / "vault"
            extra_root = base / "knowledge_sources" / "waveda_agent_kb"
            data_dir = base / "data"
            help_root.mkdir()
            note_root.mkdir()
            extra_root.mkdir(parents=True)
            (help_root / "Wave_Port.html").write_text(
                "<html><head><title>波端口</title></head><body><p>波端口用于设置激励。</p></body></html>",
                encoding="utf-8",
            )
            (extra_root / "button_location_function_index.md").write_text(
                "# 按钮位置与功能索引\n\n波端口入口位于激励源菜单，用于创建端口激励。",
                encoding="utf-8",
            )
            settings = Settings(
                project_root=base,
                waveda_help_root=help_root,
                obsidian_vault_root=note_root,
                extra_markdown_roots=[extra_root],
                data_dir=data_dir,
                embedding_model="local",
                llm_base_url="",
                llm_api_key="",
                llm_model="",
            )

            report = build_knowledge_base(settings)
            manifest = (data_dir / "raw_manifest.json").read_text(encoding="utf-8")

            self.assertEqual(report.extra_markdown_document_count, 1)
            self.assertIn("button_location_function_index.md", manifest)

    def test_pipeline_answers_with_citations_without_api_key(self):
        from raggg.config import Settings
        from raggg.pipeline.builder import build_knowledge_base
        from raggg.pipeline.rag_pipeline import RAGPipeline

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            help_root = base / "helpHtml"
            note_root = base / "vault"
            data_dir = base / "data"
            help_root.mkdir()
            note_root.mkdir()
            (help_root / "Boundary.html").write_text(
                "<html><head><title>边界</title></head><body><p>PML 是吸收边界设置。</p></body></html>",
                encoding="utf-8",
            )
            (note_root / "Absorbing.md").write_text(
                "# 吸收边界\n\n吸收边界用于减少开放区域反射。",
                encoding="utf-8",
            )
            settings = Settings(
                project_root=base,
                waveda_help_root=help_root,
                obsidian_vault_root=note_root,
                data_dir=data_dir,
                embedding_model="local",
                llm_base_url="",
                llm_api_key="",
                llm_model="",
            )
            build_knowledge_base(settings)

            answer = RAGPipeline(settings).ask("WavEDA PML 是什么？")

            self.assertIn("PML", answer.answer)
            self.assertIn("引用来源", answer.answer)
            self.assertTrue(answer.sources)
            self.assertIn("Boundary.html", answer.sources[0].chunk.relative_path)

    def test_pipeline_keeps_llm_failure_out_of_answer_body(self):
        from raggg.config import Settings
        from raggg.pipeline.builder import build_knowledge_base
        from raggg.pipeline.rag_pipeline import RAGPipeline

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            help_root = base / "helpHtml"
            note_root = base / "vault"
            data_dir = base / "data"
            help_root.mkdir()
            note_root.mkdir()
            (help_root / "Wave_Port.html").write_text(
                "<html><head><title>波端口</title></head><body><p>波端口通过激励源菜单创建，并需要选择端口所在面。</p></body></html>",
                encoding="utf-8",
            )
            settings = Settings(
                project_root=base,
                waveda_help_root=help_root,
                obsidian_vault_root=note_root,
                data_dir=data_dir,
                embedding_model="local",
                llm_base_url="https://invalid.example/v1",
                llm_api_key="bad-key",
                llm_model="deepseek-chat",
            )
            build_knowledge_base(settings)
            pipeline = RAGPipeline(settings)

            def fail_complete(_prompt: str) -> str:
                raise RuntimeError("LLM request failed: HTTP Error 401: Authorization Required")

            pipeline.client.complete = fail_complete  # type: ignore[method-assign]

            answer = pipeline.ask("波端口怎么设置？")

            self.assertIn("波端口", answer.answer)
            self.assertNotIn("HTTP Error 401", answer.answer)
            self.assertNotIn("LLM request failed", answer.answer)
            self.assertNotIn("模型调用失败", answer.answer)
            self.assertIn("模型暂不可用", answer.warning or "")

    def test_local_answer_removes_repeated_source_heading(self):
        from raggg.generation.prompt_builder import build_local_answer
        from raggg.models import Chunk
        from raggg.retrieval.retriever import SearchResult

        chunk = Chunk(
            id="wave-port-1",
            source_type="waveda_help",
            source_path="Wave_Port.html",
            relative_path="Modeling/Stimulate/Wave_Port.html",
            title="波端口",
            section="波端口",
            content="波端口 WavEDA 波端口 WavEDA中波端口通常用于模拟传输线或波导结构中的信号输入。",
            links=[],
            images=[],
            metadata={},
        )
        answer = build_local_answer(
            "波端口怎么设置？",
            [SearchResult(chunk=chunk, score=1.0, vector_score=0.5, lexical_score=0.5)],
        )

        self.assertIn("要点：", answer)
        self.assertIn("[1] 波端口：WavEDA中波端口通常用于模拟传输线或波导结构中的信号输入。", answer)
        self.assertNotIn("波端口 WavEDA 波端口", answer)

    def test_operational_prompt_uses_tutorial_sections(self):
        from raggg.generation.prompt_builder import build_prompt
        from raggg.models import Chunk
        from raggg.retrieval.retriever import SearchResult

        chunk = Chunk(
            id="wave-port-setup",
            source_type="waveda_agent_kb",
            source_path="Wave_Port.md",
            relative_path="waveda_agent_kb/10_extracted_pages/Modeling/Stimulate/Wave_Port.md",
            title="波端口",
            section="波端口设置",
            content="入口包括菜单栏-模型、工程树列表-波端口-右击、选面模式-建模界面-右击。",
            links=[],
            images=[],
            metadata={"domain": "waveda"},
        )

        prompt = build_prompt(
            "波端口怎么设置？",
            [SearchResult(chunk=chunk, score=1.0, vector_score=0.5, lexical_score=0.5)],
        )

        for section in ("入口位置", "操作步骤", "关键参数", "限制条件", "常见错误", "引用来源"):
            self.assertIn(section, prompt)

    def test_operational_local_answer_uses_tutorial_sections(self):
        from raggg.generation.prompt_builder import build_local_answer
        from raggg.models import Chunk
        from raggg.retrieval.retriever import SearchResult

        chunk = Chunk(
            id="wave-port-setup",
            source_type="waveda_agent_kb",
            source_path="Wave_Port.md",
            relative_path="waveda_agent_kb/10_extracted_pages/Modeling/Stimulate/Wave_Port.md",
            title="波端口",
            section="波端口设置",
            content="波端口入口包括菜单栏-模型、工程树列表-波端口-右击。端口面材料需为非金属，且只支持贴在Domain上的波端口。",
            links=[],
            images=[],
            metadata={"domain": "waveda"},
        )

        answer = build_local_answer(
            "波端口怎么设置？",
            [SearchResult(chunk=chunk, score=1.0, vector_score=0.5, lexical_score=0.5)],
        )

        for section in ("入口位置", "操作步骤", "关键参数", "限制条件", "常见错误", "引用来源"):
            self.assertIn(section, answer)
        self.assertIn("[1]", answer)

    def test_builder_refuses_to_overwrite_with_empty_sources(self):
        from raggg.config import Settings
        from raggg.pipeline.builder import build_knowledge_base

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data_dir = base / "data"
            settings = Settings(
                project_root=base,
                waveda_help_root=base / "missing-help",
                obsidian_vault_root=base / "missing-vault",
                data_dir=data_dir,
                embedding_model="local",
                llm_base_url="",
                llm_api_key="",
                llm_model="",
            )

            with self.assertRaises(FileNotFoundError):
                build_knowledge_base(settings)

            self.assertFalse((data_dir / "index" / "chunks.json").exists())


if __name__ == "__main__":
    unittest.main()
