# WavEDA Obsidian RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an independent desktop RAG system in `D:\RAGGG` that merges WavEDA HTML help pages and the user's multiphysics Obsidian notes.

**Architecture:** The project uses a small Python package with separated loaders, preprocessing, indexing, retrieval, generation, and desktop UI modules. The first version uses deterministic local hashed vectors plus lexical scoring so the system can build and run without downloading large models; the LLM call remains OpenAI-compatible and optional.

**Tech Stack:** Python 3.14, `unittest`, `numpy`, `tkinter`, standard-library HTML parsing and HTTP client.

---

### Task 1: Project Skeleton

**Files:**
- Create: `D:\RAGGG\src\raggg\__init__.py`
- Create: `D:\RAGGG\src\raggg\config.py`
- Create: `D:\RAGGG\requirements.txt`
- Create: `D:\RAGGG\.env.example`
- Create: `D:\RAGGG\README.md`
- Test: `D:\RAGGG\tests\test_config.py`

- [ ] **Step 1: Write failing config tests**

Create `tests\test_config.py` with tests for default paths and environment overrides.

- [ ] **Step 2: Run the config test and confirm it fails**

Run: `py -3 -m unittest tests.test_config -v`
Expected: import failure because `raggg.config` does not exist yet.

- [ ] **Step 3: Implement config and project metadata**

Create package files, `.env.example`, `requirements.txt`, and README.

- [ ] **Step 4: Run config test and confirm it passes**

Run: `py -3 -m unittest tests.test_config -v`
Expected: all tests pass.

### Task 2: Document Loaders

**Files:**
- Create: `D:\RAGGG\src\raggg\models.py`
- Create: `D:\RAGGG\src\raggg\loaders\html_loader.py`
- Create: `D:\RAGGG\src\raggg\loaders\markdown_loader.py`
- Test: `D:\RAGGG\tests\test_loaders.py`

- [ ] **Step 1: Write failing loader tests**

Tests cover HTML title/body/link/image extraction and Markdown title/wiki-link/formula extraction.

- [ ] **Step 2: Run loader tests and confirm they fail**

Run: `py -3 -m unittest tests.test_loaders -v`
Expected: import failure because loader modules do not exist yet.

- [ ] **Step 3: Implement the loaders**

Use standard-library parsers and UTF-8 reading. Return a shared `Document` dataclass.

- [ ] **Step 4: Run loader tests and confirm they pass**

Run: `py -3 -m unittest tests.test_loaders -v`
Expected: all tests pass.

### Task 3: Cleaning and Chunking

**Files:**
- Create: `D:\RAGGG\src\raggg\preprocessing\cleaner.py`
- Create: `D:\RAGGG\src\raggg\preprocessing\chunker.py`
- Test: `D:\RAGGG\tests\test_preprocessing.py`

- [ ] **Step 1: Write failing preprocessing tests**

Tests cover whitespace cleanup, template-comment removal, chunk metadata, formula preservation, and stable chunk IDs.

- [ ] **Step 2: Run preprocessing tests and confirm they fail**

Run: `py -3 -m unittest tests.test_preprocessing -v`
Expected: import failure because preprocessing modules do not exist yet.

- [ ] **Step 3: Implement cleaner and chunker**

Produce `Chunk` dataclasses with source metadata and deterministic IDs.

- [ ] **Step 4: Run preprocessing tests and confirm they pass**

Run: `py -3 -m unittest tests.test_preprocessing -v`
Expected: all tests pass.

### Task 4: Indexing and Retrieval

**Files:**
- Create: `D:\RAGGG\src\raggg\indexing\embeddings.py`
- Create: `D:\RAGGG\src\raggg\indexing\vector_store.py`
- Create: `D:\RAGGG\src\raggg\retrieval\retriever.py`
- Test: `D:\RAGGG\tests\test_retrieval.py`

- [ ] **Step 1: Write failing retrieval tests**

Tests cover deterministic vector shape, saving `vectors.npy` plus `chunks.json`, WavEDA query source weighting, and formula query source weighting.

- [ ] **Step 2: Run retrieval tests and confirm they fail**

Run: `py -3 -m unittest tests.test_retrieval -v`
Expected: import failure because indexing and retrieval modules do not exist yet.

- [ ] **Step 3: Implement embeddings, vector store, and retriever**

Use deterministic hashed vectors, cosine similarity, lexical overlap, and metadata boosts.

- [ ] **Step 4: Run retrieval tests and confirm they pass**

Run: `py -3 -m unittest tests.test_retrieval -v`
Expected: all tests pass.

### Task 5: Knowledge-Base Builder and RAG Pipeline

**Files:**
- Create: `D:\RAGGG\src\raggg\pipeline\builder.py`
- Create: `D:\RAGGG\src\raggg\pipeline\rag_pipeline.py`
- Create: `D:\RAGGG\src\raggg\generation\llm_client.py`
- Create: `D:\RAGGG\src\raggg\generation\prompt_builder.py`
- Create: `D:\RAGGG\scripts\build_knowledge_base.py`
- Create: `D:\RAGGG\scripts\smoke_test.py`
- Test: `D:\RAGGG\tests\test_pipeline.py`

- [ ] **Step 1: Write failing pipeline tests**

Tests cover building from sample roots, answering with citations without an API key, and prompt construction with source snippets.

- [ ] **Step 2: Run pipeline tests and confirm they fail**

Run: `py -3 -m unittest tests.test_pipeline -v`
Expected: import failure because pipeline modules do not exist yet.

- [ ] **Step 3: Implement builder, generation fallback, and scripts**

Builder writes `data\raw_manifest.json`, `data\processed_chunks.json`, `data\index\chunks.json`, and `data\index\vectors.npy`. The pipeline returns citation-grounded extractive answers when no API key is configured.

- [ ] **Step 4: Run pipeline tests and confirm they pass**

Run: `py -3 -m unittest tests.test_pipeline -v`
Expected: all tests pass.

### Task 6: Desktop Application

**Files:**
- Create: `D:\RAGGG\app\desktop_app.py`
- Create: `D:\RAGGG\src\raggg\desktop\main_window.py`
- Test: `D:\RAGGG\tests\test_desktop_import.py`

- [ ] **Step 1: Write failing desktop import test**

Test imports the desktop module and verifies the application class exists without opening a visible window.

- [ ] **Step 2: Run desktop test and confirm it fails**

Run: `py -3 -m unittest tests.test_desktop_import -v`
Expected: import failure because desktop modules do not exist yet.

- [ ] **Step 3: Implement tkinter desktop shell**

Three-pane layout: history/status, chat, sources. Provide ask and rebuild buttons.

- [ ] **Step 4: Run desktop test and confirm it passes**

Run: `py -3 -m unittest tests.test_desktop_import -v`
Expected: all tests pass.

### Task 7: Full Build, Verification, and Docs

**Files:**
- Create: `D:\RAGGG\docs\user_guide.md`
- Create: `D:\RAGGG\docs\progress\2026-07-03-rag-build-progress.md`
- Modify: `D:\RAGGG\README.md`

- [ ] **Step 1: Run the full test suite**

Run: `py -3 -m unittest discover -s tests -v`
Expected: all tests pass.

- [ ] **Step 2: Build the real merged knowledge base**

Run: `py -3 scripts\build_knowledge_base.py`
Expected: generated chunk and vector files under `D:\RAGGG\data`.

- [ ] **Step 3: Run smoke questions**

Run: `py -3 scripts\smoke_test.py`
Expected: each question returns sources.

- [ ] **Step 4: Write usage docs and progress log**

Document how to build, ask, launch desktop app, and what was verified.

- [ ] **Step 5: Final verification**

Run: `py -3 -m unittest discover -s tests -v` and `py -3 scripts\smoke_test.py`.
Expected: tests pass and smoke questions return cited answers.
