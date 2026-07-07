from __future__ import annotations

import csv
import json
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

from raggg.models import Document


SUPPORTED_USER_EXTENSIONS = {
    ".csv",
    ".docx",
    ".htm",
    ".html",
    ".json",
    ".jsonl",
    ".md",
    ".pdf",
    ".txt",
    ".xlsx",
}


class _TextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self._parts.append(text)

    def text(self) -> str:
        return "\n".join(self._parts)


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_html(path: Path) -> str:
    parser = _TextHTMLParser()
    parser.feed(_read_text(path))
    return parser.text()


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - exercised when dependency is absent.
        raise RuntimeError("PDF 解析需要安装 pypdf。") from exc

    reader = PdfReader(str(path))
    pages: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append(f"第 {index} 页\n{text}")
    return "\n\n".join(pages)


def _read_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as package:
        xml = package.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        parts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def _shared_strings(package: zipfile.ZipFile) -> list[str]:
    try:
        xml = package.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ElementTree.fromstring(xml)
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    values: list[str] = []
    for item in root.findall(".//x:si", namespace):
        values.append("".join(node.text or "" for node in item.findall(".//x:t", namespace)))
    return values


def _cell_value(cell: ElementTree.Element, shared: list[str]) -> str:
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//x:t", namespace)).strip()
    value = cell.find("x:v", namespace)
    if value is None or value.text is None:
        return ""
    text = value.text.strip()
    if cell_type == "s":
        try:
            return shared[int(text)]
        except (ValueError, IndexError):
            return text
    return text


def _read_xlsx(path: Path) -> str:
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as package:
        shared = _shared_strings(package)
        sheet_names = sorted(
            name for name in package.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", name)
        )
        sheets: list[str] = []
        for index, name in enumerate(sheet_names, start=1):
            root = ElementTree.fromstring(package.read(name))
            rows: list[str] = []
            for row in root.findall(".//x:row", namespace):
                values = [_cell_value(cell, shared) for cell in row.findall("x:c", namespace)]
                values = [value for value in values if value]
                if values:
                    rows.append(" | ".join(values))
            if rows:
                sheets.append(f"工作表 {index}\n" + "\n".join(rows))
    return "\n\n".join(sheets)


def _read_csv(path: Path) -> str:
    rows: list[str] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        for row in csv.reader(handle):
            values = [value.strip() for value in row if value.strip()]
            if values:
                rows.append(" | ".join(values))
    return "\n".join(rows)


def _read_json(path: Path) -> str:
    text = _read_text(path)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text
    return json.dumps(data, ensure_ascii=False, indent=2)


def _title_from_text(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:80]
    return fallback


def load_user_document(path: Path, root: Path) -> Document:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_USER_EXTENSIONS:
        raise ValueError(f"Unsupported user document type: {suffix}")

    if suffix in {".md", ".txt", ".jsonl"}:
        text = _read_text(path)
    elif suffix in {".html", ".htm"}:
        text = _read_html(path)
    elif suffix == ".csv":
        text = _read_csv(path)
    elif suffix == ".json":
        text = _read_json(path)
    elif suffix == ".pdf":
        text = _read_pdf(path)
    elif suffix == ".docx":
        text = _read_docx(path)
    elif suffix == ".xlsx":
        text = _read_xlsx(path)
    else:  # pragma: no cover - guarded above.
        text = ""

    return Document(
        source_type="user_dropbox",
        source_path=path,
        relative_path=_relative(path, root),
        title=_title_from_text(text, path.stem),
        text=text or f"{path.name} 暂未提取到可检索文本。",
        metadata={
            "domain": "user",
            "content_type": "user_document",
            "file_extension": suffix,
        },
    )


def iter_user_documents(root: Path) -> list[Document]:
    if not root.exists():
        return []
    docs: list[Document] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        if path.suffix.lower() not in SUPPORTED_USER_EXTENSIONS:
            continue
        docs.append(load_user_document(path, root))
    return docs
