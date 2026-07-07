import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def write_docx(path: Path, text: str) -> None:
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>"
        + text
        + "</w:t></w:r></w:p></w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("word/document.xml", xml)


def write_xlsx(path: Path, values: list[str]) -> None:
    shared = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        + "".join(f"<si><t>{value}</t></si>" for value in values)
        + "</sst>"
    )
    cells = "".join(f'<c r="A{index + 1}" t="s"><v>{index}</v></c>' for index in range(len(values)))
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData><row r=\"1\">{cells}</row></sheetData></worksheet>"
    )
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("xl/sharedStrings.xml", shared)
        package.writestr("xl/worksheets/sheet1.xml", sheet)


def write_pdf(path: Path, text: str) -> None:
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
    )
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 18 Tf 50 240 Td ({text}) Tj ET".encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    with path.open("wb") as handle:
        writer.write(handle)


class UserDropboxTests(unittest.TestCase):
    def test_loader_reads_pdf_docx_and_xlsx(self):
        from raggg.loaders.user_file_loader import iter_user_documents

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_pdf(root / "guide.pdf", "Wave port PDF text")
            write_docx(root / "manual.docx", "棱柱创建参数")
            write_xlsx(root / "table.xlsx", ["波端口", "积分线"])

            docs = iter_user_documents(root)
            texts = "\n".join(doc.text for doc in docs)

            self.assertEqual(len(docs), 3)
            self.assertIn("Wave port PDF text", texts)
            self.assertIn("棱柱创建参数", texts)
            self.assertIn("波端口", texts)
            self.assertIn("积分线", texts)
            self.assertEqual({doc.source_type for doc in docs}, {"user_dropbox"})

    def test_copy_to_dropbox_keeps_supported_files_and_renames_collisions(self):
        from raggg.pipeline.dropbox import copy_to_dropbox

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "incoming"
            dropbox = base / "dropbox"
            source.mkdir()
            (source / "note.txt").write_text("平面波", encoding="utf-8")
            (source / "ignore.exe").write_text("skip", encoding="utf-8")
            (dropbox / "incoming").mkdir(parents=True)
            (dropbox / "incoming" / "note.txt").write_text("old", encoding="utf-8")

            report = copy_to_dropbox([source], dropbox)

            self.assertEqual(len(report.imported), 1)
            self.assertEqual(report.imported[0].name, "note_1.txt")
            self.assertEqual(report.imported[0].read_text(encoding="utf-8"), "平面波")

    def test_builder_includes_user_dropbox_documents(self):
        from raggg.config import Settings
        from raggg.pipeline.builder import build_knowledge_base

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            help_root = base / "helpHtml"
            vault_root = base / "vault"
            dropbox = base / "knowledge_sources" / "user_dropbox"
            data_dir = base / "data"
            help_root.mkdir()
            vault_root.mkdir()
            dropbox.mkdir(parents=True)
            (help_root / "Wave_Port.html").write_text("<html><body>波端口</body></html>", encoding="utf-8")
            write_docx(dropbox / "custom.docx", "用户补充资料：探针设置")
            settings = Settings(
                project_root=base,
                waveda_help_root=help_root,
                obsidian_vault_root=vault_root,
                data_dir=data_dir,
                embedding_model="local",
                llm_base_url="",
                llm_api_key="",
                llm_model="",
                extra_markdown_roots=[base / "knowledge_sources"],
                user_dropbox_root=dropbox,
            )

            report = build_knowledge_base(settings)
            manifest = (data_dir / "raw_manifest.json").read_text(encoding="utf-8")

            self.assertEqual(report.user_document_count, 1)
            self.assertIn("user_dropbox", manifest)
            self.assertIn("custom.docx", manifest)


if __name__ == "__main__":
    unittest.main()
