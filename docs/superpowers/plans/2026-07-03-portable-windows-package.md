# Portable Windows Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a copy-and-run Windows portable folder for the WavEDA RAG system.

**Architecture:** Create `D:\RAGGG-Portable` as a self-contained folder with a Python runtime, installed dependencies, source code, built index data, relative `.env`, and `start.bat`. Keep the original development project in `D:\RAGGG` and use copy operations only; no source data mutation.

**Tech Stack:** Windows PowerShell, Python embedded/runtime, PySide6, numpy, batch launcher.

---

### Task 1: Prepare Portable Layout

**Files:**
- Create: `D:\RAGGG-Portable\start.bat`
- Create: `D:\RAGGG-Portable\README-Portable.md`
- Create: `D:\RAGGG-Portable\config\.env`
- Copy: `app`, `src`, `scripts`, `data`, `requirements.txt`

- [ ] Create target directories without deleting existing files.
- [ ] Copy project files and index data into the portable folder.
- [ ] Write relative config paths.

### Task 2: Add Python Runtime

**Files:**
- Create: `D:\RAGGG-Portable\runtime\python`

- [ ] Use the existing project `.venv` runtime if it can be made relocatable enough for this folder.
- [ ] If not, download and prepare Python embeddable runtime.
- [ ] Install or copy `numpy` and `PySide6` into the portable runtime.

### Task 3: Portable Launcher

**Files:**
- Create: `D:\RAGGG-Portable\start.bat`

- [ ] Set `PYTHONPATH` to the copied `src`.
- [ ] Set `RAGGG_PORTABLE_ROOT` to the launcher directory.
- [ ] Launch `app\desktop_app.py` using the bundled runtime.

### Task 4: Code Support

**Files:**
- Modify: `D:\RAGGG\src\raggg\config.py`
- Modify: `D:\RAGGG\app\desktop_app.py`
- Test: existing unit tests

- [ ] Add support for `RAGGG_PORTABLE_ROOT` and relative env values.
- [ ] Keep normal development startup working.
- [ ] Verify tests still pass.

### Task 5: Verification

**Files:**
- Use: `D:\RAGGG-Portable\start.bat`

- [ ] Run portable Python import checks.
- [ ] Run smoke retrieval from the portable folder.
- [ ] Launch the portable desktop app and confirm the process starts.
