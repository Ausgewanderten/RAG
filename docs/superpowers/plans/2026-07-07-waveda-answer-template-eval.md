# WavEDA Answer Template And Eval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add stable operation-style answer templates and a WavEDA QA evaluation suite.

**Architecture:** Keep retrieval unchanged except where tests expose ranking gaps. Add question intent helpers in the generation layer, use them in prompt/local-answer construction, and add a standalone evaluation script that checks source hits and required answer terms without calling the LLM.

**Tech Stack:** Python standard library, existing `unittest`, existing local vector store and PySide6 app.

## Global Constraints

- Keep all outputs under `D:\RAGGG` and sync runtime changes to `D:\RAGGG-Portable`.
- Do not delete files or directories in bulk.
- Keep the portable bundle copy-and-run.
- Do not expose API keys in output, docs, tests, or scripts.

---

### Task 1: Operation Answer Template

**Files:**
- Modify: `tests/test_pipeline.py`
- Modify: `src/raggg/generation/prompt_builder.py`

**Interfaces:**
- Produces: `is_operational_question(question: str) -> bool`
- Produces: operation answers containing `入口位置`, `操作步骤`, `关键参数`, `限制条件`, `常见错误`, `引用来源`

- [ ] Write failing tests for operation prompt and local fallback template.
- [ ] Run targeted tests and confirm failure.
- [ ] Implement intent detection and template generation.
- [ ] Run targeted tests and confirm pass.

### Task 2: QA Evaluation Suite

**Files:**
- Create: `tests/fixtures/waveda_eval_cases.json`
- Create: `scripts/evaluate_waveda_qa.py`
- Create: `tests/test_eval_suite.py`

**Interfaces:**
- Evaluation case fields: `id`, `question`, `expected_source_contains`, `required_terms`
- Script output: `PASS <id>` / `FAIL <id>` lines and summary counts.

- [ ] Write fixture and schema/runner tests.
- [ ] Run tests and confirm failure before runner exists.
- [ ] Implement runner using `RAGPipeline`.
- [ ] Run runner and tests.

### Task 3: Sync And Verify Portable

**Files:**
- Modify mirrored files under `D:\RAGGG-Portable`

- [ ] Copy changed source, tests where useful, scripts, and README into portable bundle.
- [ ] Run main test suite.
- [ ] Run evaluation script.
- [ ] Verify portable window loads the updated index.
