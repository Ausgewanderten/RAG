from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from raggg.config import Settings, get_user_dropbox_root
from raggg.indexing.embeddings import HashedEmbeddingModel
from raggg.indexing.vector_store import VectorStore
from raggg.loaders.html_loader import iter_html_documents
from raggg.loaders.markdown_loader import iter_markdown_documents
from raggg.loaders.user_file_loader import iter_user_documents
from raggg.models import Chunk, Document
from raggg.preprocessing.chunker import chunk_documents
from raggg.pipeline.source_state import write_source_state


@dataclass(frozen=True)
class BuildReport:
    document_count: int
    chunk_count: int
    waveda_document_count: int
    obsidian_document_count: int
    extra_markdown_document_count: int
    user_document_count: int
    data_dir: Path


def _document_manifest(documents: list[Document]) -> list[dict[str, str]]:
    return [
        {
            "source_type": doc.source_type,
            "source_path": str(doc.source_path),
            "relative_path": doc.relative_path,
            "title": doc.title,
        }
        for doc in documents
    ]


def _write_chunks(path: Path, chunks: list[Chunk]) -> None:
    path.write_text(
        json.dumps([chunk.to_dict() for chunk in chunks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def build_knowledge_base(settings: Settings) -> BuildReport:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    documents = []
    user_dropbox_root = get_user_dropbox_root(settings)
    waveda_docs = iter_html_documents(settings.waveda_help_root)
    obsidian_docs = iter_markdown_documents(settings.obsidian_vault_root)
    extra_docs = []
    for root in settings.extra_markdown_roots:
        root_docs = iter_markdown_documents(
            root,
            source_type="waveda_agent_kb",
            domain="waveda",
            content_type="agent_kb",
        )
        extra_docs.extend(
            doc for doc in root_docs if not _is_relative_to(doc.source_path, user_dropbox_root)
        )
    user_docs = iter_user_documents(user_dropbox_root)
    documents.extend(waveda_docs)
    documents.extend(obsidian_docs)
    documents.extend(extra_docs)
    documents.extend(user_docs)
    if not documents:
        raise FileNotFoundError(
            "No source documents were found. Check WAVEDA_HELP_ROOT, OBSIDIAN_VAULT_ROOT, RAG_EXTRA_MARKDOWN_ROOTS, and RAG_USER_DROPBOX_ROOT before rebuilding."
        )

    chunks = chunk_documents(documents)
    (settings.data_dir / "raw_manifest.json").write_text(
        json.dumps(_document_manifest(documents), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_chunks(settings.data_dir / "processed_chunks.json", chunks)
    store = VectorStore.from_chunks(chunks, HashedEmbeddingModel())
    store.save(settings.data_dir / "index")
    write_source_state(settings)

    return BuildReport(
        document_count=len(documents),
        chunk_count=len(chunks),
        waveda_document_count=len(waveda_docs),
        obsidian_document_count=len(obsidian_docs),
        extra_markdown_document_count=len(extra_docs),
        user_document_count=len(user_docs),
        data_dir=settings.data_dir,
    )
