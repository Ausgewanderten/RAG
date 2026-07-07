from __future__ import annotations

import re

from raggg.retrieval.retriever import SearchResult


OPERATION_TERMS = (
    "怎么",
    "如何",
    "怎样",
    "设置",
    "创建",
    "添加",
    "入口",
    "在哪",
    "哪里",
    "位置",
    "报错",
    "错误",
    "失败",
    "排查",
    "建不了",
    "无法",
)
OPERATION_SECTIONS = ("入口位置", "操作步骤", "关键参数", "限制条件", "常见错误", "引用来源")


def is_operational_question(question: str) -> bool:
    normalized = question.lower().replace(" ", "")
    if any(term in normalized for term in OPERATION_TERMS):
        return True
    return "howto" in normalized or "how-to" in normalized


def build_prompt(question: str, sources: list[SearchResult]) -> str:
    snippets = []
    for index, result in enumerate(sources, start=1):
        chunk = result.chunk
        snippets.append(
            f"[{index}] {chunk.title} | {chunk.source_type} | {chunk.relative_path}\n"
            f"{chunk.content[:900]}"
        )
    joined = "\n\n".join(snippets)
    base = (
        "你是一个中文 RAG 助手。只根据给定资料回答；资料不足时说明不足。\n\n"
        f"问题：{question}\n\n"
        f"资料：\n{joined}\n\n"
    )
    if is_operational_question(question):
        return (
            base
            + "这是 WavEDA 操作型问题。请严格按以下小标题回答，缺失资料的部分写“资料未明确说明”：\n"
            + "\n".join(f"{index}. {section}" for index, section in enumerate(OPERATION_SECTIONS, start=1))
            + "\n每个可验证步骤后标注引用编号，例如 [1]。"
        )
    return base + "请给出简洁、可操作的回答，并列出引用。"


def build_local_answer(question: str, sources: list[SearchResult]) -> str:
    if not sources:
        return "资料中没有足够依据回答这个问题。"
    if is_operational_question(question):
        return _build_operational_local_answer(sources)
    top = sources[:3]
    lines = ["根据当前知识库，先给出可确认的信息。", "", "要点："]
    for index, result in enumerate(top, start=1):
        chunk = result.chunk
        snippet = _source_snippet(chunk.title, chunk.content)
        lines.append(f"- [{index}] {chunk.title}：{snippet}")
    lines.append("")
    lines.append("引用来源：")
    for index, result in enumerate(top, start=1):
        chunk = result.chunk
        lines.append(f"[{index}] {chunk.title} | {chunk.source_type} | {chunk.relative_path}")
    return "\n".join(lines)


def _build_operational_local_answer(sources: list[SearchResult]) -> str:
    top = sources[:4]
    lines = ["根据当前知识库，整理成可操作步骤。", "", "要点："]
    for index, result in enumerate(top[:2], start=1):
        chunk = result.chunk
        lines.append(f"- [{index}] {chunk.title}：{_source_snippet(chunk.title, chunk.content)}")
    lines.extend(
        [
            "",
            "入口位置：",
            _best_snippet_line(top, ("入口", "菜单", "右击", "工具栏", "工程树", "选面", "选点")),
            "",
            "操作步骤：",
            _best_snippet_line(top, ("步骤", "创建", "设置", "选择", "点击", "双击", "输入")),
            "",
            "关键参数：",
            _best_snippet_line(top, ("参数", "名称", "材料", "模式", "方向", "频率", "半径", "高度", "电势")),
            "",
            "限制条件：",
            _best_snippet_line(top, ("必须", "只支持", "不支持", "注意", "需", "不能", "限制")),
            "",
            "常见错误：",
            _best_snippet_line(top, ("报错", "错误", "失败", "异常", "日志", "警告", "排查")),
            "",
            "引用来源：",
        ]
    )
    for index, result in enumerate(top, start=1):
        chunk = result.chunk
        lines.append(f"[{index}] {chunk.title} | {chunk.source_type} | {chunk.relative_path}")
    return "\n".join(lines)


def _best_snippet_line(sources: list[SearchResult], keywords: tuple[str, ...]) -> str:
    fallback = "资料未明确说明。"
    for index, result in enumerate(sources, start=1):
        chunk = result.chunk
        content = re.sub(r"\s+", " ", chunk.content).strip()
        if any(keyword.lower() in content.lower() for keyword in keywords):
            return f"- [{index}] {chunk.title}：{_source_snippet(chunk.title, content)}"
    return f"- {fallback}"


def _source_snippet(title: str, content: str, limit: int = 180) -> str:
    snippet = re.sub(r"\s+", " ", content).strip()
    prefix_tokens = (title, "WavEDA")
    changed = True
    while changed:
        changed = False
        for token in prefix_tokens:
            trimmed = _strip_heading_token(snippet, token)
            if trimmed != snippet:
                snippet = trimmed
                changed = True
    if len(snippet) <= limit:
        return snippet
    return snippet[:limit].rstrip(" ，。；、") + "..."


def _strip_heading_token(text: str, token: str) -> str:
    if not token or not text.startswith(token):
        return text
    rest = text[len(token) :]
    if rest and rest[0] not in " \t\r\n：:-|":
        return text
    return rest.strip(" ：:-|")
