from __future__ import annotations

import re
from dataclasses import dataclass

from raggg.config import Settings
from raggg.generation.llm_client import OpenAICompatibleClient
from raggg.generation.prompt_builder import build_local_answer, build_prompt
from raggg.indexing.vector_store import VectorStore
from raggg.retrieval.retriever import Retriever, SearchResult


@dataclass(frozen=True)
class RAGAnswer:
    question: str
    answer: str
    sources: list[SearchResult]
    warning: str | None = None


class RAGPipeline:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = VectorStore.load(settings.data_dir / "index")
        self.retriever = Retriever(self.store)
        self.client = OpenAICompatibleClient(
            settings.llm_base_url,
            settings.llm_api_key,
            settings.llm_model,
        )

    def ask(self, question: str, top_k: int = 6) -> RAGAnswer:
        sources = self.retriever.search(question, top_k=top_k)
        prompt = build_prompt(question, sources)
        warning = None
        if self.client.is_configured:
            try:
                answer = self.client.complete(prompt)
                if self._answer_denies_existing_evidence(question, answer, sources):
                    answer = build_local_answer(question, sources)
                    warning = (
                        "\u6a21\u578b\u56de\u7b54\u4e0e\u5df2\u68c0\u7d22"
                        "\u8d44\u6599\u4e0d\u4e00\u81f4\uff0c\u5df2\u81ea\u52a8"
                        "\u6539\u7528\u672c\u5730\u8bc1\u636e\u56de\u7b54\u3002"
                    )
            except RuntimeError as exc:
                answer = build_local_answer(question, sources)
                warning = self._friendly_llm_warning(str(exc))
        else:
            answer = build_local_answer(question, sources)
        return RAGAnswer(question=question, answer=answer, sources=sources, warning=warning)

    @staticmethod
    def _answer_denies_existing_evidence(
        question: str,
        answer: str,
        sources: list[SearchResult],
    ) -> bool:
        denial_markers = (
            "\u672a\u627e\u5230\u5173\u4e8e",  # 未找到关于
            "\u6ca1\u6709\u627e\u5230\u5173\u4e8e",  # 没有找到关于
            "\u4efb\u4f55\u63cf\u8ff0",  # 任何描述
            "\u672a\u6d89\u53ca",  # 未涉及
            "\u65e0\u6cd5\u56de\u7b54",  # 无法回答
        )
        if not any(marker in answer for marker in denial_markers):
            return False
        terms = RAGPipeline._question_terms(question)
        if not terms:
            return False
        for result in sources:
            chunk = result.chunk
            haystack = f"{chunk.title}\n{chunk.relative_path}\n{chunk.content}".lower()
            if any(term in haystack for term in terms):
                return True
        return False

    @staticmethod
    def _question_terms(question: str) -> set[str]:
        compact = re.sub(r"\s+", "", question)
        return {
            term.lower()
            for term in re.findall(r"[A-Za-z][A-Za-z0-9_-]{1,}", compact)
            if len(term) >= 2
        }

    @staticmethod
    def _friendly_llm_warning(error_message: str) -> str:
        if "401" in error_message or "Authorization" in error_message:
            return "模型暂不可用：API 认证失败，已使用本地知识库回答。请检查 DeepSeek API key。"
        return "模型暂不可用，已使用本地知识库回答。"
