from __future__ import annotations

from collections import Counter, defaultdict
from configparser import ConfigParser
from html.parser import HTMLParser
from pathlib import Path
import csv
import html
import json
import re
import xml.etree.ElementTree as ET


APP = Path(r"D:\Staid\app\waveda")
OUT = Path(r"D:\vscode_projects\agent\knowledge_base\waveda_agent_kb")

ERROR_DIR = OUT / "40_error_cases"
EXAMPLE_DIR = OUT / "40_example_cases"
MATERIAL_DIR = OUT / "50_material_library"
COMPONENT_DIR = OUT / "60_circuit_components"
ICON_DIR = OUT / "70_ui_icons"
INDEX_DIR = OUT / "20_indexes"
TOPIC_DIR = OUT / "30_topic_cards"


ERROR_WORDS = (
    "失败",
    "错误",
    "无法",
    "不能",
    "不允许",
    "请检查",
    "警告",
    "异常",
    "无效",
    "为空",
    "不存在",
    "Failed",
    "Error",
    "Unable",
    "Invalid",
    "Warning",
    "wrong",
    "Wrong",
    "fail",
)


SKIP_HTML_PHRASES = (
    "提示：所有绿色注释下面的区域是替换的部分",
    "下面是标题",
    "下面是介绍",
    "下面是超链接",
    "本文涉及模块",
    "如需多个则按照下两行复制",
    "类型、时间、参与编辑人数",
)


def ensure_dirs():
    for directory in (ERROR_DIR, EXAMPLE_DIR, MATERIAL_DIR, COMPONENT_DIR, ICON_DIR, INDEX_DIR, TOPIC_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def attrs_from_text(tag_text: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for key, value in re.findall(r'([A-Za-z0-9_\-:]+)\s*=\s*"([^"]*)"', tag_text):
        attrs[key] = html.unescape(value)
    return attrs


def rel(path: Path) -> str:
    return str(path).replace("\\", "/")


def rel_to_out(path: Path) -> str:
    return str(path.relative_to(OUT)).replace("\\", "/")


class ExampleHTMLExtractor(HTMLParser):
    def __init__(self, source_file: Path):
        super().__init__(convert_charrefs=True)
        self.source_file = source_file
        self.title = ""
        self.header = ""
        self.parts: list[str] = []
        self.images: list[dict[str, str]] = []
        self.buf: list[str] = []
        self.in_title = False
        self.heading_level: int | None = None
        self.in_li = False
        self._last = ""

    def handle_starttag(self, tag: str, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.in_title = True
            self.buf = []
        elif re.fullmatch(r"h[1-6]", tag):
            self.flush()
            self.heading_level = int(tag[1])
            self.buf = []
        elif tag in ("p", "div"):
            self.flush()
        elif tag == "br":
            self.flush()
        elif tag == "li":
            self.flush()
            self.in_li = True
            self.buf = []
        elif tag == "img":
            self.flush()
            src = (attrs.get("src") or attrs.get("SRC") or "").strip().strip("\"'")
            if src:
                abs_img = (self.source_file.parent / src).resolve()
                self.images.append({"src": src, "abs_path": str(abs_img)})
                self.parts.append(f"> 图片: `{src}`  \n> 原始路径: `{abs_img}`")

    def handle_endtag(self, tag: str):
        if tag == "title":
            text = self.clean("".join(self.buf))
            if text:
                self.title = text
            self.buf = []
            self.in_title = False
        elif re.fullmatch(r"h[1-6]", tag):
            text = self.clean("".join(self.buf))
            if text:
                if tag == "h1" and not self.header:
                    self.header = text
                level = min((self.heading_level or 2) + 1, 6)
                self.parts.append(f'{"#" * level} {text}')
            self.buf = []
            self.heading_level = None
        elif tag in ("p", "div"):
            self.flush()
        elif tag == "li":
            text = self.clean("".join(self.buf))
            if text:
                self.parts.append(f"- {text}")
            self.buf = []
            self.in_li = False

    def handle_data(self, data: str):
        if data:
            self.buf.append(data)

    def clean(self, text: str) -> str:
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        for phrase in SKIP_HTML_PHRASES:
            if phrase in text:
                return ""
        return text

    def flush(self):
        if self.in_title or self.heading_level is not None or self.in_li:
            return
        text = self.clean("".join(self.buf))
        if text and text != self._last:
            self.parts.append(text)
            self._last = text
        self.buf = []

    def result(self):
        self.flush()
        return self.header or self.title or self.source_file.stem, self.parts, self.images


def parse_xml_text(text: str):
    try:
        return ET.fromstring(text), ""
    except ET.ParseError as exc:
        return None, str(exc)


def first_tag_attrs(text: str, tag: str) -> dict[str, str]:
    match = re.search(rf"<{re.escape(tag)}\b([^>]*)>", text, flags=re.I)
    if not match:
        return {}
    return attrs_from_text(match.group(1))


def all_tag_attrs(text: str, tag: str) -> list[dict[str, str]]:
    return [attrs_from_text(match.group(1)) for match in re.finditer(rf"<{re.escape(tag)}\b([^>]*)>", text, flags=re.I)]


def count_tag(text: str, tag: str) -> int:
    return len(re.findall(rf"<{re.escape(tag)}\b", text, flags=re.I))


def parse_tsp(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {"exists": False}

    text = read_text(path)
    root, error = parse_xml_text(text)
    result = {
        "exists": True,
        "source": str(path),
        "parse_error": error,
        "project": {},
        "units": {},
        "solver": {},
        "domain": {},
        "frequencies": [],
        "variables": [],
        "materials": [],
        "counts": {},
    }

    if root is not None:
        result["project"] = dict(root.attrib)
        unit = root.find(".//project-unit")
        solver = root.find(".//project-solver")
        domain = root.find(".//domain-space")
        result["units"] = dict(unit.attrib) if unit is not None else {}
        result["solver"] = dict(solver.attrib) if solver is not None else {}
        result["domain"] = dict(domain.attrib) if domain is not None else {}
        result["frequencies"] = [dict(node.attrib) for node in root.findall(".//frequency-pulse")]
        result["variables"] = [dict(node.attrib) for node in root.findall(".//variables/var")]
        result["materials"] = [node.attrib.get("name", "") for node in root.findall(".//materials/material") if node.attrib.get("name")]
        for tag in ("face", "solid", "curve", "material", "lumped-port", "wave-port", "point-source", "plane-wave", "far-field"):
            result["counts"][tag] = len(root.findall(f".//{tag}"))
        return result

    result["project"] = first_tag_attrs(text, "project")
    result["units"] = first_tag_attrs(text, "project-unit")
    result["solver"] = first_tag_attrs(text, "project-solver")
    result["domain"] = first_tag_attrs(text, "domain-space")
    result["frequencies"] = all_tag_attrs(text, "frequency-pulse")
    result["variables"] = all_tag_attrs(text, "var")
    result["materials"] = [attrs.get("name", "") for attrs in all_tag_attrs(text, "material") if attrs.get("name")]
    for tag in ("face", "solid", "curve", "material", "lumped-port", "wave-port", "point-source", "plane-wave", "far-field"):
        result["counts"][tag] = count_tag(text, tag)
    return result


def md_table(rows: list[list[str]], headers: list[str]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        safe = [str(cell).replace("\n", " ").replace("|", "/") for cell in row]
        lines.append("| " + " | ".join(safe) + " |")
    return "\n".join(lines)


def extract_examples():
    rows = []
    for html_file in sorted((APP / "Example").rglob("*.html")):
        raw = read_text(html_file)
        parser = ExampleHTMLExtractor(html_file)
        parser.feed(raw)
        title, parts, images = parser.result()

        category = html_file.relative_to(APP / "Example").parts[0]
        tsp_file = html_file.with_suffix(".tsp")
        tsp = parse_tsp(tsp_file)
        case_rel = html_file.relative_to(APP / "Example")
        out_file = EXAMPLE_DIR / case_rel.with_suffix(".md")

        freq_rows = []
        for freq in tsp.get("frequencies", [])[:8]:
            freq_rows.append(
                [
                    freq.get("physics-type", ""),
                    freq.get("type", ""),
                    freq.get("start", ""),
                    freq.get("end", ""),
                    freq.get("point", ""),
                    freq.get("step", ""),
                    freq.get("sweep_method", ""),
                    freq.get("method", ""),
                ]
            )

        counts = tsp.get("counts", {})
        summary_lines = [
            f"# {title}",
            "",
            f"- 案例分类: `{category}`",
            f"- 来源 HTML: `{html_file}`",
            f"- 工程文件: `{tsp_file if tsp_file.exists() else '未找到同名 .tsp'}`",
            f"- 截图数量: {len(images)}",
            "",
            "## 工程摘要",
            "",
            f"- 工程类型: `{tsp.get('project', {}).get('type', '')}`",
            f"- WavEDA 版本: `{tsp.get('project', {}).get('waveda_version', '')}`",
            f"- 坐标类型: `{tsp.get('project', {}).get('coor', '')}`",
            f"- 单位: `{json.dumps(tsp.get('units', {}), ensure_ascii=False)}`",
            f"- 求解器: `{json.dumps(tsp.get('solver', {}), ensure_ascii=False)}`",
            f"- 计算区域/Domain: `{json.dumps(tsp.get('domain', {}), ensure_ascii=False)}`",
            f"- 变量数量: {len(tsp.get('variables', []))}",
            f"- 材料: {', '.join(tsp.get('materials', [])[:20]) or '未抽取到'}",
            f"- 对象数量: face={counts.get('face', 0)}, solid={counts.get('solid', 0)}, curve={counts.get('curve', 0)}, lumped-port={counts.get('lumped-port', 0)}, wave-port={counts.get('wave-port', 0)}, point-source={counts.get('point-source', 0)}, plane-wave={counts.get('plane-wave', 0)}, far-field={counts.get('far-field', 0)}",
        ]
        if tsp.get("parse_error"):
            summary_lines.append(f"- XML 解析提示: `{tsp['parse_error']}`（已使用容错抽取）")
        if freq_rows:
            summary_lines.extend(
                [
                    "",
                    "### 频率/激励设置摘要",
                    "",
                    md_table(freq_rows, ["physics", "type", "start", "end", "point", "step", "sweep_method", "method"]),
                ]
            )
        if tsp.get("variables"):
            var_rows = [[v.get("name", ""), v.get("expression", "")] for v in tsp["variables"][:40]]
            summary_lines.extend(["", "### 变量摘要", "", md_table(var_rows, ["变量", "表达式"])])

        body = "\n\n".join(parts).strip()
        image_lines = ["## 图片资源", ""]
        for idx, image in enumerate(images, 1):
            image_lines.append(f'{idx}. `{image["src"]}` -> `{image["abs_path"]}`')

        write(out_file, "\n".join(summary_lines) + "\n\n## 案例教程抽取\n\n" + body + "\n\n" + "\n".join(image_lines))

        rows.append(
            {
                "category": category,
                "title": title,
                "source_html": str(html_file),
                "source_tsp": str(tsp_file) if tsp_file.exists() else "",
                "kb_file": rel_to_out(out_file),
                "project_type": tsp.get("project", {}).get("type", ""),
                "variables": len(tsp.get("variables", [])),
                "materials": len(tsp.get("materials", [])),
                "images": len(images),
                "parse_error": tsp.get("parse_error", ""),
            }
        )

    index_lines = [
        "# 示例案例索引",
        "",
        "本目录从 `D:\\Staid\\app\\waveda\\Example` 抽取案例 HTML、同名 `.tsp` 工程摘要和截图路径。适合回答“有没有类似案例”“这个案例怎么设置材料/频率/端口/网格/后处理”。",
        "",
    ]
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["category"]].append(row)
    for category, items in sorted(grouped.items()):
        index_lines.append(f"## {category}")
        table_rows = [
            [
                item["title"],
                item["project_type"],
                str(item["variables"]),
                str(item["materials"]),
                str(item["images"]),
                f'[{item["kb_file"]}](../{item["kb_file"]})',
            ]
            for item in sorted(items, key=lambda x: x["title"])
        ]
        index_lines.append(md_table(table_rows, ["案例", "工程类型", "变量", "材料", "截图", "知识页"]))
        index_lines.append("")
    write(EXAMPLE_DIR / "index.md", "\n".join(index_lines))

    with (EXAMPLE_DIR / "example_manifest.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)
    return rows


def classify_error(text: str) -> str:
    text_lower = text.lower()
    if any(word in text for word in ("端口", "波端口", "集总")) or "port" in text_lower:
        return "端口/激励"
    if any(word in text for word in ("网格", "剖分")) or "mesh" in text_lower:
        return "网格"
    if any(word in text for word in ("仿真", "求解器", "求解")) or "simulation" in text_lower or "solver" in text_lower:
        return "仿真/求解"
    if any(word in text for word in ("文件", "保存", "导入", "导出", "路径")) or any(word in text_lower for word in ("file", "save", "import", "export", "path")):
        return "文件/导入导出"
    if any(word in text for word in ("材料", "材质")) or "material" in text_lower:
        return "材料"
    if any(word in text for word in ("参数", "格式", "输入", "变量", "数值")) or any(word in text_lower for word in ("parameter", "format", "input", "variable")):
        return "参数/输入格式"
    if any(word in text for word in ("选择", "选中", "面", "体", "线", "曲线", "几何")) or any(word in text_lower for word in ("selected", "face", "solid", "curve")):
        return "几何/选择"
    if any(word in text for word in ("连接", "许可证", "许可")) or "license" in text_lower:
        return "连接/许可"
    return "其他"


def solution_hint(category: str, text: str) -> str:
    if category == "端口/激励":
        return "检查端口创建时的选择对象、端口面是否为平面、是否贴合 Domain、导体数量/电势设置是否变化；必要时重新创建端口或重新运行波端口。"
    if category == "网格":
        return "检查网格类型、求解器是否匹配，查看病态网格；适当调整 3D 网格、波端口网格或自适应网格参数。"
    if category == "仿真/求解":
        return "先运行验证，检查频率、求解器、Domain、材料、端口/激励是否完整；查看详细日志定位失败阶段。"
    if category == "文件/导入导出":
        return "检查文件路径、后缀、权限、文件是否为空或被占用；导入数据时检查格式与分隔符。"
    if category == "材料":
        return "检查材料名称是否重复、材料模块是否支持当前物理场、参数格式和损耗设置是否正确。"
    if category == "参数/输入格式":
        return "按提示检查输入格式，例如坐标 `(u,v,w)`、数值范围、变量名和单位；不要在非单位界面额外带单位。"
    if category == "几何/选择":
        return "检查当前选择模式和对象类型；面/线/点数量是否满足操作要求，曲面、非共面或非闭合曲线常会导致失败。"
    if category == "连接/许可":
        return "检查许可证服务、网络连接、软件配置路径和服务是否运行。"
    return "结合原始提示、当前操作阶段和帮助文档限制进一步排查。"


def extract_language_messages():
    ts_files = sorted((APP / "resources" / "language").glob("*.ts"))
    all_rows = []
    error_rows = []
    for ts_file in ts_files:
        try:
            tree = ET.parse(ts_file)
        except ET.ParseError:
            continue
        for context in tree.findall(".//context"):
            context_name = context.findtext("name", default="")
            for message in context.findall("message"):
                source = "".join(message.findtext("source", default="").splitlines()).strip()
                trans_node = message.find("translation")
                translation = "".join("".join(trans_node.itertext()).splitlines()).strip() if trans_node is not None else ""
                if not source and not translation:
                    continue
                row = {
                    "file": ts_file.name,
                    "context": context_name,
                    "source": source,
                    "translation": translation,
                }
                all_rows.append(row)
                combined = f"{source} {translation}"
                if any(word in combined for word in ERROR_WORDS):
                    category = classify_error(combined)
                    err = dict(row)
                    err["category"] = category
                    err["suggested_check"] = solution_hint(category, combined)
                    error_rows.append(err)

    for target, rows in ((ERROR_DIR / "raw_ui_messages.csv", all_rows), (ERROR_DIR / "error_message_index.csv", error_rows)):
        with target.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["file", "context", "source", "translation"])
            if rows:
                writer.writeheader()
                writer.writerows(rows)

    grouped = defaultdict(list)
    for row in error_rows:
        grouped[row["category"]].append(row)

    lines = [
        "# 真实 UI 报错/警告文案索引",
        "",
        "本文件从 `resources/language/*.ts` 抽取，包含软件真实弹窗、日志、验证失败和 UI 错误提示。解决建议为基于文案类别生成的初筛检查项，需要结合具体模型和日志确认。",
        "",
        f"- UI 文案总数: {len(all_rows)}",
        f"- 错误/警告候选数: {len(error_rows)}",
        "",
        "## 分类统计",
        "",
    ]
    lines.append(md_table([[cat, str(len(items))] for cat, items in sorted(grouped.items())], ["分类", "数量"]))
    lines.append("")
    for category, items in sorted(grouped.items()):
        lines.append(f"## {category}")
        table_rows = [
            [
                item["file"],
                item["source"][:120],
                item["translation"][:120],
                item["suggested_check"],
            ]
            for item in items[:120]
        ]
        lines.append(md_table(table_rows, ["文件", "英文/原文", "中文提示", "初筛检查建议"]))
        if len(items) > 120:
            lines.append(f"\n该分类还有 {len(items) - 120} 条，完整内容见 `error_message_index.csv`。")
        lines.append("")
    write(ERROR_DIR / "error_message_index.md", "\n".join(lines))
    return all_rows, error_rows


def extract_materials():
    source = APP / "library" / "material" / "waveda_material.lib"
    root = ET.parse(source).getroot()
    rows = []
    for material in root.findall(".//material"):
        em = material.find("em-material")
        thermal = material.find("thermal-material")
        modules = material.find("material-modules")
        ela = material.find("ela-material")
        regular = (em.attrib.get("EM-regular", "") if em is not None else "").split(",")
        regular = [item.strip() for item in regular]
        rows.append(
            {
                "name": material.attrib.get("name", ""),
                "modules": ",".join([k for k, v in (modules.attrib.items() if modules is not None else []) if v == "1"]),
                "em_type": em.attrib.get("type", "") if em is not None else "",
                "epsilon_r": regular[0] if len(regular) > 0 else "",
                "conductivity": regular[1] if len(regular) > 1 else "",
                "mu_r": regular[2] if len(regular) > 2 else "",
                "loss_tan": em.attrib.get("loss-tan", "") if em is not None else "",
                "thermal_rho": thermal.attrib.get("rho", "") if thermal is not None else "",
                "thermal_cp": thermal.attrib.get("cp", "") if thermal is not None else "",
                "thermal_kappa": thermal.attrib.get("kappa", "") if thermal is not None else "",
                "elastic_rho": ela.attrib.get("rho", "") if ela is not None else "",
            }
        )

    with (MATERIAL_DIR / "material_index.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# WavEDA 内置材料库索引",
        "",
        f"- 来源: `{source}`",
        f"- 材料数量: {len(rows)}",
        "",
        "## 材料表",
        "",
        md_table(
            [
                [
                    row["name"],
                    row["modules"],
                    row["em_type"],
                    row["epsilon_r"],
                    row["conductivity"],
                    row["mu_r"],
                    row["loss_tan"],
                    row["thermal_kappa"],
                ]
                for row in rows
            ],
            ["材料", "支持模块", "EM类型", "epsilon_r", "电导率", "mu_r", "损耗角正切", "导热系数"],
        ),
    ]
    write(MATERIAL_DIR / "materials.md", "\n".join(lines))

    guide = """# 材料选择指南

## 使用方式

- 查材料是否存在：先看 `material_index.csv` 或 `materials.md`。
- 查电磁仿真参数：重点看 `em_type`、`epsilon_r`、`conductivity`、`mu_r`、`loss_tan`。
- 查热仿真参数：重点看 `thermal_rho`、`thermal_cp`、`thermal_kappa`。
- 查多物理场可用性：看 `modules` 是否包含 `EM`、`Thermal`、`Ela`、`Piezo`。

## 新手常见判断

- `PEC` 常用于理想金属导体。
- `Air` 常用于背景材料或空气盒子。
- `FR-4` 类材料常用于 PCB/微带天线基板，应关注介电常数和损耗角正切。
- 金属材料通常关注电导率；介质材料通常关注介电常数和损耗角正切。

## 排错提示

- 如果材料损耗没有生效，检查材料设置中损耗角正切选项是否启用。
- 如果多物理场结果异常，检查材料是否启用了对应物理模块。
- 如果材料名重复或导入失败，检查自定义材料名是否已存在。
"""
    write(MATERIAL_DIR / "material_selection_guide.md", guide)
    return rows


def clean_component_name(stem: str) -> str:
    return re.sub(r"^[0-9A-Za-z](?=[A-Z_])", "", stem)


def extract_components():
    ini = APP / "resources" / "component" / "componentSetting.ini"
    parser = ConfigParser(strict=False)
    parser.optionxform = str
    parser.read(ini, encoding="utf-8")
    names = dict(parser.items("Name")) if parser.has_section("Name") else {}
    tips = dict(parser.items("Tip")) if parser.has_section("Tip") else {}

    rows = []
    for file in sorted((APP / "resources" / "component").rglob("*")):
        if not file.is_file() or file.name == "componentSetting.ini":
            continue
        category = file.parent.name
        raw = file.stem
        identifier = clean_component_name(raw)
        display = names.get(identifier) or names.get(raw) or identifier
        tip = tips.get(identifier) or tips.get(raw) or ""
        rows.append(
            {
                "category": category,
                "identifier": identifier,
                "display": display.replace("\\r\\n", " / "),
                "tip": tip.replace("\\r\\n", " / "),
                "icon_path": str(file),
            }
        )

    with (COMPONENT_DIR / "component_icon_index.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    grouped = defaultdict(list)
    for row in rows:
        grouped[row["category"]].append(row)
    lines = [
        "# 电路组件与图标索引",
        "",
        f"- 来源目录: `{APP / 'resources' / 'component'}`",
        f"- 显示名称配置: `{ini}`",
        f"- 组件图标数量: {len(rows)}",
        "",
    ]
    for category, items in sorted(grouped.items()):
        lines.append(f"## {category}")
        lines.append(md_table([[i["identifier"], i["display"], i["tip"], i["icon_path"]] for i in items], ["组件标识", "显示名", "提示", "图标路径"]))
        lines.append("")
    write(COMPONENT_DIR / "component_index.md", "\n".join(lines))
    return rows


def guess_icon_category(name: str) -> str:
    lower = name.lower()
    if any(x in lower for x in ("run", "stop", "pause", "check", "clear")):
        return "仿真/运行"
    if "mesh" in lower:
        return "网格"
    if "waveport" in lower or "lumpedport" in lower or "port" in lower:
        return "端口"
    if any(x in lower for x in ("export", "import", "save", "open", "new")):
        return "文件/导入导出"
    if lower.startswith("view") or "zoom" in lower:
        return "视图"
    if any(x in lower for x in ("solid", "face", "line", "box", "sphere", "cylinder", "cone", "torous", "bondwire")):
        return "建模"
    if any(x in lower for x in ("material", "frequency", "domain", "unit", "solver", "variable", "var")):
        return "设计设置"
    if any(x in lower for x in ("result", "farfield", "s_params", "smith")):
        return "结果/后处理"
    return "其他"


def extract_icons():
    toolbar = APP / "resources" / "icons" / "toolbar"
    rows = []
    for file in sorted(toolbar.iterdir()):
        if file.is_file():
            rows.append(
                {
                    "category": guess_icon_category(file.stem),
                    "icon_name": file.stem,
                    "extension": file.suffix,
                    "path": str(file),
                }
            )
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["category"]].append(row)

    with (ICON_DIR / "toolbar_icon_index.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# 工具栏图标索引",
        "",
        f"- 来源目录: `{toolbar}`",
        f"- 图标数量: {len(rows)}",
        "",
        "该索引根据文件名进行初步功能分类，实际界面显示名需结合帮助文档和翻译文件确认。",
        "",
    ]
    for category, items in sorted(grouped.items()):
        lines.append(f"## {category}")
        lines.append(md_table([[i["icon_name"], i["extension"], i["path"]] for i in items], ["图标名", "类型", "路径"]))
        lines.append("")
    write(ICON_DIR / "toolbar_icon_index.md", "\n".join(lines))
    return rows


def extract_module_descriptions():
    desc_dir = APP / "resources" / "module_description"
    rows = []
    for file in sorted(desc_dir.glob("*.txt")):
        text = read_text(file).strip()
        rows.append({"file": file.name, "module": file.stem, "text": text})

    lines = ["# 模块能力索引", "", f"- 来源目录: `{desc_dir}`", ""]
    for row in rows:
        lines.append(f"## {row['module']}")
        lines.append(row["text"])
        lines.append("")
    write(INDEX_DIR / "module_capability_index.md", "\n".join(lines))

    cn_rows = [row for row in rows if row["module"].endswith("_CN")]
    guide_lines = [
        "# WavEDA 模块选择指南",
        "",
        "本指南根据 `resources/module_description/*_CN.txt` 初步整理，用于回答“我该用哪个模块”。",
        "",
    ]
    for row in cn_rows:
        name = row["module"].replace("_CN", "")
        guide_lines.append(f"## {name}")
        guide_lines.append(row["text"])
        guide_lines.append("")
    guide_lines.extend(
        [
            "## 快速选择",
            "",
            "- 做 S 参数、端口、天线、滤波器、远场、场分布：优先 EM。",
            "- 做电路原理图、SPICE、电路滤波器、端口网络：优先 Circuit。",
            "- 做温度、热源、导热：优先 Thermal。",
            "- 做结构力学、应力、位移：优先 Mechnical。",
            "- 做电-热-力耦合、封装可靠性、焦耳热/热膨胀/电磁力：优先 Multi-Physics。",
        ]
    )
    write(TOPIC_DIR / "module_selection_guide.md", "\n".join(guide_lines))
    return rows


def main():
    ensure_dirs()
    examples = extract_examples()
    ui_rows, error_rows = extract_language_messages()
    materials = extract_materials()
    components = extract_components()
    icons = extract_icons()
    modules = extract_module_descriptions()

    summary = {
        "examples": len(examples),
        "ui_messages": len(ui_rows),
        "error_candidates": len(error_rows),
        "materials": len(materials),
        "components": len(components),
        "toolbar_icons": len(icons),
        "module_descriptions": len(modules),
    }
    write(OUT / "_extra_extraction_summary.json", json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
