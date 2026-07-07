import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class RetrievalTests(unittest.TestCase):
    def test_hashed_embedding_is_deterministic(self):
        from raggg.indexing.embeddings import HashedEmbeddingModel

        model = HashedEmbeddingModel(dimensions=32)

        first = model.embed_text("波端口 设置")
        second = model.embed_text("波端口 设置")

        self.assertEqual(first.shape, (32,))
        self.assertTrue((first == second).all())

    def test_vector_store_saves_chunks_and_vectors(self):
        from raggg.indexing.embeddings import HashedEmbeddingModel
        from raggg.indexing.vector_store import VectorStore
        from raggg.models import Chunk

        chunk = Chunk(
            id="c1",
            source_type="waveda_help",
            source_path=r"D:\help\Wave_Port.html",
            relative_path="Wave_Port.html",
            title="波端口",
            section="波端口",
            content="波端口用于设置端口激励。",
            metadata={"domain": "waveda"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            store = VectorStore.from_chunks([chunk], HashedEmbeddingModel(dimensions=16))
            store.save(Path(tmp))

            self.assertTrue((Path(tmp) / "chunks.json").exists())
            self.assertTrue((Path(tmp) / "vectors.npy").exists())

    def test_waveda_query_prefers_waveda_help(self):
        from raggg.indexing.embeddings import HashedEmbeddingModel
        from raggg.indexing.vector_store import VectorStore
        from raggg.models import Chunk
        from raggg.retrieval.retriever import Retriever

        chunks = [
            Chunk("w1", "waveda_help", "help", "Wave_Port.html", "波端口", "波端口", "波端口用于设置端口激励和模式。", metadata={"domain": "waveda"}),
            Chunk("n1", "obsidian_note", "note", "端口理论.md", "端口理论", "端口理论", "端口是电磁能量进入系统的边界。", metadata={"domain": "multiphysics"}),
        ]
        store = VectorStore.from_chunks(chunks, HashedEmbeddingModel(dimensions=32))
        results = Retriever(store).search("WavEDA 波端口怎么设置", top_k=2)

        self.assertEqual(results[0].chunk.source_type, "waveda_help")

    def test_formula_query_prefers_formula_chunk(self):
        from raggg.indexing.embeddings import HashedEmbeddingModel
        from raggg.indexing.vector_store import VectorStore
        from raggg.models import Chunk
        from raggg.retrieval.retriever import Retriever

        chunks = [
            Chunk("outline", "obsidian_note", "note", "计划.md", "学习计划", "计划", "学习 Maxwell 方程组的目标和任务。", metadata={"domain": "multiphysics", "has_formula": False}),
            Chunk("formula", "obsidian_note", "note", "Maxwell.md", "Maxwell", "公式", "$$\\nabla \\cdot D = \\rho$$\nMaxwell 方程组描述电磁场。", metadata={"domain": "multiphysics", "has_formula": True}),
        ]
        store = VectorStore.from_chunks(chunks, HashedEmbeddingModel(dimensions=32))
        results = Retriever(store).search("什么是 Maxwell 方程组公式", top_k=2)

        self.assertEqual(results[0].chunk.id, "formula")

    def test_definition_query_prefers_exact_title_note(self):
        from raggg.indexing.embeddings import HashedEmbeddingModel
        from raggg.indexing.vector_store import VectorStore
        from raggg.models import Chunk
        from raggg.retrieval.retriever import Retriever

        chunks = [
            Chunk("task", "obsidian_note", "note", "1.2.md", "1.2 总电荷与总电流形式的 Maxwell 方程", "关键推导", "用 Gauss 定理推导 Maxwell 方程。$$\\nabla \\cdot D = \\rho$$", metadata={"domain": "multiphysics", "has_formula": True}),
            Chunk("definition", "obsidian_note", "note", "Maxwell方程组是什么.md", "Maxwell 方程组是什么", "定义", "Maxwell 方程组是经典电磁学的核心方程。", metadata={"domain": "multiphysics", "has_formula": False}),
        ]
        store = VectorStore.from_chunks(chunks, HashedEmbeddingModel(dimensions=32))
        results = Retriever(store).search("什么是 Maxwell 方程组", top_k=2)

        self.assertEqual(results[0].chunk.id, "definition")

    def test_pml_query_prefers_boundary_page_over_generic_waveda_page(self):
        from raggg.indexing.embeddings import HashedEmbeddingModel
        from raggg.indexing.vector_store import VectorStore
        from raggg.models import Chunk
        from raggg.retrieval.retriever import Retriever

        chunks = [
            Chunk("options", "waveda_help", "help", "File/Options.html", "选项", "选项", "WavEDA 许可证和显示配置。", metadata={"domain": "waveda"}),
            Chunk("boundary", "waveda_help", "help", "EM_Project/Boundary.html", "边界", "开放边界", "开放边界包括一阶吸收边界 ABC 和完美匹配层 PML。", metadata={"domain": "waveda"}),
        ]
        store = VectorStore.from_chunks(chunks, HashedEmbeddingModel(dimensions=32))
        results = Retriever(store).search("WavEDA 里的 PML 和吸收边界有什么关系", top_k=2)

        self.assertEqual(results[0].chunk.id, "boundary")

    def test_waveda_context_prefers_help_over_theory_note(self):
        from raggg.indexing.embeddings import HashedEmbeddingModel
        from raggg.indexing.vector_store import VectorStore
        from raggg.models import Chunk
        from raggg.retrieval.retriever import Retriever

        chunks = [
            Chunk("help", "waveda_help", "help", "EM_Project/Boundary.html", "边界", "PML", "WavEDA 中 PML 是开放边界的一种设置。", metadata={"domain": "waveda", "has_formula": False}),
            Chunk("note", "obsidian_note", "note", "吸收边界.md", "吸收边界", "PML 理论", "$$\\nabla \\times E$$\nPML 是吸收边界理论。", metadata={"domain": "multiphysics", "has_formula": True}),
        ]
        store = VectorStore.from_chunks(chunks, HashedEmbeddingModel(dimensions=32))
        results = Retriever(store).search("WavEDA 中 PML 怎么理解", top_k=2)

        self.assertEqual(results[0].chunk.id, "help")

    def test_waveda_agent_kb_is_treated_as_waveda_source(self):
        from raggg.indexing.embeddings import HashedEmbeddingModel
        from raggg.indexing.vector_store import VectorStore
        from raggg.models import Chunk
        from raggg.retrieval.retriever import Retriever

        chunks = [
            Chunk("note", "obsidian_note", "note", "端口理论.md", "端口理论", "端口理论", "端口是电磁能量进入系统的边界。", metadata={"domain": "multiphysics"}),
            Chunk("agent", "waveda_agent_kb", "kb", "30_topic_cards/ports.md", "端口设置流程", "波端口", "波端口入口位于激励源菜单，适合创建端口激励。", metadata={"domain": "waveda"}),
        ]
        store = VectorStore.from_chunks(chunks, HashedEmbeddingModel(dimensions=32))
        results = Retriever(store).search("WavEDA 波端口入口在哪里", top_k=2)

        self.assertEqual(results[0].chunk.id, "agent")

    def test_waveda_agent_kb_troubleshooting_card_beats_generic_example(self):
        from raggg.indexing.embeddings import HashedEmbeddingModel
        from raggg.indexing.vector_store import VectorStore
        from raggg.models import Chunk
        from raggg.retrieval.retriever import Retriever

        chunks = [
            Chunk("example", "waveda_agent_kb", "kb", "40_example_cases/Circuit/Filter.md", "WavEDA", "案例", "WavEDA 示例工程。", metadata={"domain": "waveda"}),
            Chunk("trouble", "waveda_agent_kb", "kb", "30_topic_cards/troubleshooting_and_constraints.md", "排错与约束卡", "先看哪里", "报错和警告应先查看日志、验证结果和网格病态区域。", metadata={"domain": "waveda"}),
        ]
        store = VectorStore.from_chunks(chunks, HashedEmbeddingModel(dimensions=32))
        results = Retriever(store).search("WavEDA 报错怎么排查？", top_k=2)

        self.assertEqual(results[0].chunk.id, "trouble")

    def test_waveda_agent_kb_material_guide_beats_geometry_page(self):
        from raggg.indexing.embeddings import HashedEmbeddingModel
        from raggg.indexing.vector_store import VectorStore
        from raggg.models import Chunk
        from raggg.retrieval.retriever import Retriever

        chunks = [
            Chunk("torus", "waveda_agent_kb", "kb", "10_extracted_pages/Modeling/Create_3D_Geometry/Torus.md", "环", "材料", "可以设置名称、材料、透明度和颜色。", metadata={"domain": "waveda"}),
            Chunk("material", "waveda_agent_kb", "kb", "50_material_library/material_selection_guide.md", "材料选择指南", "使用方式", "查材料是否存在，先看材料库；电磁仿真参数重点看介电常数、电导率和损耗角正切。", metadata={"domain": "waveda"}),
        ]
        store = VectorStore.from_chunks(chunks, HashedEmbeddingModel(dimensions=32))
        results = Retriever(store).search("材料库怎么选材料？", top_k=2)

        self.assertEqual(results[0].chunk.id, "material")

    def test_user_dropbox_filename_phrase_beats_generic_notes(self):
        from raggg.indexing.embeddings import HashedEmbeddingModel
        from raggg.indexing.vector_store import VectorStore
        from raggg.models import Chunk
        from raggg.retrieval.retriever import Retriever

        chunks = [
            Chunk(
                "generic",
                "obsidian_note",
                "note",
                "01-基础概念/端口是什么.md",
                "端口是什么",
                "端口是什么",
                "端口、后处理、网格划分和边界条件是多物理场仿真的基础概念。",
                metadata={"domain": "multiphysics"},
            ),
            Chunk(
                "smart",
                "user_dropbox",
                "dropbox",
                "Smart E Book.docx",
                "1.Cultural Dialogue",
                "1.Cultural Dialogue",
                "Smart E Book contains cultural dialogue materials, correction tables, grammar notes, and oral English practice content.",
                metadata={"domain": "user"},
            ),
        ]
        store = VectorStore.from_chunks(chunks, HashedEmbeddingModel(dimensions=32))
        results = Retriever(store).search("Smart Ebook里面有什么?", top_k=2)

        self.assertEqual(results[0].chunk.id, "smart")

    def test_user_dropbox_compact_english_term_beats_definition_notes(self):
        from raggg.indexing.embeddings import HashedEmbeddingModel
        from raggg.indexing.vector_store import VectorStore
        from raggg.models import Chunk
        from raggg.retrieval.retriever import Retriever

        chunks = [
            Chunk(
                "generic",
                "obsidian_note",
                "note",
                "01-基础概念/Maxwell方程组是什么.md",
                "Maxwell 方程组是什么",
                "定义",
                "Maxwell 方程组、端口和边界条件是电磁仿真的基础概念。",
                metadata={"domain": "multiphysics"},
            ),
            Chunk(
                "sfgen",
                "user_dropbox",
                "dropbox",
                "SFgen_prcv.pdf",
                "Symbol and Footprint Database",
                "Abstract",
                "SFgen is an automatic electronic component library construction pipeline for symbol and footprint generation.",
                metadata={"domain": "user"},
            ),
        ]
        store = VectorStore.from_chunks(chunks, HashedEmbeddingModel(dimensions=32))
        results = Retriever(store).search("SFgen是什么?", top_k=2)

        self.assertEqual(results[0].chunk.id, "sfgen")

    def test_specific_geometry_name_beats_generic_setting_page(self):
        from raggg.indexing.embeddings import HashedEmbeddingModel
        from raggg.indexing.vector_store import VectorStore
        from raggg.models import Chunk
        from raggg.retrieval.retriever import Retriever

        chunks = [
            Chunk("setting", "waveda_help", "help", "Tool/Design_Setting.html", "设计设置", "设置", "设置材料和默认选项。", metadata={"domain": "waveda"}),
            Chunk("prism", "waveda_help", "help", "Modeling/Create_3D_Geometry/Prism.html", "棱柱", "棱柱", "此对话框用于创建棱柱形状物体。", metadata={"domain": "waveda"}),
        ]
        store = VectorStore.from_chunks(chunks, HashedEmbeddingModel(dimensions=32))
        results = Retriever(store).search("怎么设置棱柱？", top_k=2)

        self.assertEqual(results[0].chunk.id, "prism")

    def test_real_index_prism_query_returns_prism_page_first(self):
        from raggg.config import Settings
        from raggg.indexing.vector_store import VectorStore
        from raggg.retrieval.retriever import Retriever

        index_dir = ROOT / "data" / "index"
        if not (index_dir / "chunks.json").exists():
            self.skipTest("real index has not been built")

        settings = Settings.from_env({"RAG_DATA_DIR": str(ROOT / "data")})
        store = VectorStore.load(settings.data_dir / "index")
        results = Retriever(store).search("怎么设置棱柱？", top_k=5)

        self.assertEqual(results[0].chunk.relative_path, "Modeling/Create_3D_Geometry/Prism.html")

    def test_real_index_error_query_prefers_troubleshooting_over_examples(self):
        from raggg.config import Settings
        from raggg.indexing.vector_store import VectorStore
        from raggg.retrieval.retriever import Retriever

        index_dir = ROOT / "data" / "index"
        if not (index_dir / "chunks.json").exists():
            self.skipTest("real index has not been built")

        settings = Settings.from_env({"RAG_DATA_DIR": str(ROOT / "data")})
        store = VectorStore.load(settings.data_dir / "index")
        results = Retriever(store).search("WavEDA 报错怎么排查？", top_k=3)

        self.assertNotIn("40_example_cases", results[0].chunk.relative_path)


if __name__ == "__main__":
    unittest.main()
