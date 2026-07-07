from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
import html
import json
import re


SRC = Path(r"D:\Staid\app\waveda\documentation\helpHtml")
DOC_ROOT = Path(r"D:\Staid\app\waveda\documentation")
OUT = Path(r"D:\vscode_projects\agent\knowledge_base\waveda_agent_kb")
EXTRACTED = OUT / "10_extracted_pages"
INDEXES = OUT / "20_indexes"
TOPICS = OUT / "30_topic_cards"
TEMPLATES = OUT / "90_maintenance_templates"

SKIP_PHRASES = [
    "提示：所有绿色注释下面的区域是替换的部分",
    "下面是标题",
    "下面是介绍",
    "下面是空行符",
    "下面是超链接",
    "本文涉及模块",
    "把复制到你想放图片的位置即可",
    "这个是图片插入的代码",
    "如需多个则按照下两行复制",
    "不需要则删除",
    "类型、时间、参与编辑人数",
]

DISPLAY_DIRS = {
    "File": "文件与主页",
    "Modeling": "建模总览",
    "Bkg_Mat": "背景与材料",
    "Design": "设计设置",
    "Create_3D_Geometry": "创建体",
    "Create_Face": "创建面",
    "Create_Curve": "创建曲线",
    "Model_Editing": "模型编辑",
    "Stimulate": "激励与端口",
    "Mesh": "网格",
    "Simulation": "仿真",
    "Post_Processing": "后处理",
    "EM_Project": "EM设计与结果",
    "Observer": "接收器",
    "Tool": "工具",
    "View": "视图",
    "helpHtml": "基础介绍",
}

CONSTRAINT_RE = re.compile(
    r"报错|错误|警告|失败|无法|不能|不可|不支持|必须|注意|建议|检查|限制|默认|收敛|过大|过小|超过|小于|大于"
)
BUTTON_RE = re.compile(r"点击|双击|右键|主菜单栏|工具栏|下拉|勾选|选择|按钮|图标")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[。；;！!？?])\s*")


class MDExtractor(HTMLParser):
    def __init__(self, src_file: Path):
        super().__init__(convert_charrefs=True)
        self.src_file = src_file
        self.parts: list[str] = []
        self.buf: list[str] = []
        self.title = ""
        self.in_title = False
        self.heading_level: int | None = None
        self.in_li = False
        self.current_href = ""
        self.links: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self._last_text = ""

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
                abs_img = (self.src_file.parent / src).resolve()
                self.images.append({"src": src, "abs_path": str(abs_img)})
                self.parts.append(f"> 图片: `{src}`  \n> 原始路径: `{abs_img}`")
        elif tag == "a":
            self.current_href = (attrs.get("href") or "").strip()

    def handle_endtag(self, tag: str):
        if tag == "title":
            text = self.clean("".join(self.buf))
            if text:
                self.title = text
            self.buf = []
            self.in_title = False
        elif re.fullmatch(r"h[1-6]", tag):
            text = self.clean("".join(self.buf))
            if text and text != "WavEDA":
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
        elif tag == "a":
            text = self.clean("".join(self.buf))
            if self.current_href and text:
                self.links.append({"text": text, "href": self.current_href})
            self.current_href = ""

    def handle_data(self, data: str):
        if data:
            self.buf.append(data)

    def clean(self, text: str) -> str:
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        for phrase in SKIP_PHRASES:
            if phrase in text:
                return ""
        return text

    def flush(self):
        if self.in_title or self.heading_level is not None or self.in_li:
            return
        text = self.clean("".join(self.buf))
        if text and text != "WavEDA" and text != self._last_text:
            self.parts.append(text)
            self._last_text = text
        self.buf = []

    def result(self):
        self.flush()
        return self.title, self.parts, self.images, self.links


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def rel_to_out(path: Path) -> str:
    return str(path.relative_to(OUT)).replace("\\", "/")


def extract_pages():
    EXTRACTED.mkdir(parents=True, exist_ok=True)
    INDEXES.mkdir(parents=True, exist_ok=True)
    TOPICS.mkdir(parents=True, exist_ok=True)
    TEMPLATES.mkdir(parents=True, exist_ok=True)

    records = []
    by_module = defaultdict(list)
    constraints = []
    button_candidates = []

    for src_file in sorted(SRC.rglob("*.html")):
        raw = src_file.read_text(encoding="utf-8", errors="replace")
        parser = MDExtractor(src_file)
        parser.feed(raw)
        title, parts, images, links = parser.result()
        if not title:
            title = src_file.stem

        rel = src_file.relative_to(SRC)
        module = rel.parts[0] if len(rel.parts) > 1 else "helpHtml"
        section = rel.parts[1] if len(rel.parts) > 2 else ""
        out_md = EXTRACTED / rel.with_suffix(".md")

        header = [
            f"# {title}",
            "",
            f"- 来源 HTML: `{src_file}`",
            f"- 原始相对路径: `{rel.as_posix()}`",
            f"- 知识模块: `{DISPLAY_DIRS.get(module, module)}`",
            "",
            "## 正文抽取",
            "",
        ]
        body = "\n\n".join(parts).strip() or "（该页未抽取到有效正文，可能是占位页或格式异常。）"

        img_section = ""
        if images:
            img_lines = ["## 图片资源", ""]
            for i, im in enumerate(images, 1):
                img_lines.append(f'{i}. `{im["src"]}` -> `{im["abs_path"]}`')
            img_section = "\n\n" + "\n".join(img_lines)

        link_section = ""
        if links:
            link_lines = ["## 页内/相关链接", ""]
            seen_links = set()
            for lnk in links:
                key = (lnk["text"], lnk["href"])
                if key in seen_links:
                    continue
                seen_links.add(key)
                link_lines.append(f'- {lnk["text"]}: `{lnk["href"]}`')
            link_section = "\n\n" + "\n".join(link_lines)

        write(out_md, "\n".join(header) + body + img_section + link_section)

        text = "\n".join(parts)
        for sentence in SENTENCE_SPLIT_RE.split(text):
            sentence = sentence.strip()
            if 8 <= len(sentence) <= 260 and CONSTRAINT_RE.search(sentence):
                constraints.append(
                    {
                        "module": module,
                        "title": title,
                        "source": rel_to_out(out_md),
                        "text": sentence,
                    }
                )
            if 10 <= len(sentence) <= 260 and BUTTON_RE.search(sentence):
                button_candidates.append(
                    {
                        "module": module,
                        "title": title,
                        "source": rel_to_out(out_md),
                        "text": sentence,
                    }
                )

        rec = {
            "title": title,
            "module": module,
            "section": section,
            "source_html": str(src_file),
            "source_rel": rel.as_posix(),
            "extracted_md": rel_to_out(out_md),
            "image_count": len(images),
            "link_count": len(links),
        }
        records.append(rec)
        by_module[module].append(rec)

    return records, by_module, constraints, button_candidates


def write_readme(records, by_module):
    module_lines = []
    for module, items in sorted(by_module.items(), key=lambda kv: (DISPLAY_DIRS.get(kv[0], kv[0]), kv[0])):
        module_lines.append(f"- `{module}`（{DISPLAY_DIRS.get(module, module)}）：{len(items)} 页")

    write(
        OUT / "00_README.md",
        f"""# WavEDA 使用教导 Agent 知识库（第一版）

本目录由 `D:\\Staid\\app\\waveda\\documentation` 下的 WavEDA 帮助文档首次提炼生成，目标是服务“新手使用教导 Agent”：回答按钮位置、功能解释、仿真流程、仿真方法差异、常见限制与排错方向等问题。

## 目录结构

- `00_README.md`：本说明。
- `01_agent_usage_guide.md`：给后续 Agent/RAG 使用的回答策略。
- `20_indexes/`：索引层，适合检索入口和导航。
- `30_topic_cards/`：面向新手问答的专题卡片。
- `10_extracted_pages/`：从原始 HTML 逐页抽取的 Markdown，保留原始来源与图片路径。
- `90_maintenance_templates/`：后续补充报错、按钮、案例时可直接复制的模板。
- `_source_manifest.jsonl`：每页来源、模块、图片数量、抽取文件路径清单。
- `_extract_waveda_kb.py`：本次提炼脚本，后续可复用刷新知识库。

## 已抽取范围

- 原始 HTML 页数：{len(records)}
- 图片未复制入库，Markdown 中保留原始图片绝对路径，避免第一版知识库过大。

## 模块页数

{chr(10).join(module_lines)}

## 使用建议

1. 新手问答优先检索 `30_topic_cards/`，再回到 `10_extracted_pages/` 查源文。
2. 涉及“按钮在哪里”的问题，优先查 `20_indexes/button_location_function_index.md`。
3. 涉及“为什么不能仿真/报错如何解决”，优先查 `30_topic_cards/troubleshooting_and_constraints.md`。
4. 涉及“仿真方法怎么选”，优先查 `30_topic_cards/simulation_methods_comparison.md`。
5. 如果后续收集到真实报错文本，请补到 `90_maintenance_templates/error_case_template.md` 或新建 `40_error_cases/`。
""",
    )


def write_agent_guide():
    write(
        OUT / "01_agent_usage_guide.md",
        """# Agent 使用指南

## 回答定位

这个知识库的目标用户是 WavEDA 新手。回答应优先给出“该点哪里、为什么、怎么做、出错怎么办”的可执行说明，而不是只复述文档。

## 推荐回答结构

- 入口位置：说明菜单、工程树、工具栏或右键位置。
- 操作步骤：按 1、2、3 列出最短路径。
- 参数含义：解释用户会看到的关键字段。
- 适用场景：说明什么时候应该用这个功能。
- 常见限制：列出必须满足的条件。
- 排错建议：告诉用户去哪里看日志、如何缩小问题。
- 来源追溯：引用 `10_extracted_pages` 中的具体页面。

## 检索优先级

1. 新手流程、仿真方法、排错等综合问题：先查 `30_topic_cards`。
2. 按钮/入口/右键菜单：先查 `20_indexes/button_location_function_index.md`。
3. 某个具体功能名：查 `20_indexes/module_page_index.md` 后进入抽取页。
4. 图片定位：抽取页的“图片资源”保留了原始截图路径，可打开原图核对按钮位置。

## 回答边界

第一版主要来自官方帮助文档。原文中没有完整的报错代码库，因此遇到具体报错时应：

- 先让用户提供完整日志文本、操作步骤、模型设置和截图。
- 用 `troubleshooting_and_constraints.md` 中的“限制/必须/不支持”规则做初筛。
- 明确区分“文档明确说明”和“根据限制推断”。
""",
    )


def write_indexes(records, by_module, constraints, button_candidates):
    write(OUT / "_source_manifest.jsonl", "\n".join(json.dumps(r, ensure_ascii=False) for r in records))

    lines = ["# 模块与页面索引", "", "按原始帮助文档目录归类。每条链接指向已抽取 Markdown，页面顶部有原始 HTML 路径。", ""]
    for module, items in sorted(by_module.items(), key=lambda kv: (DISPLAY_DIRS.get(kv[0], kv[0]), kv[0])):
        lines.append(f"## {DISPLAY_DIRS.get(module, module)} (`{module}`)")
        for r in sorted(items, key=lambda x: x["source_rel"]):
            lines.append(f'- {r["title"]} -> [{r["source_rel"]}](../{r["extracted_md"]})')
        lines.append("")
    write(INDEXES / "module_page_index.md", "\n".join(lines))

    workflow_refs = [
        ("认识软件与文件入口", "File/Homepage.md", "新建、打开、保存工程，重置工程。"),
        ("设置全局单位", "Modeling/Design/Unit.md", "长度、时间、频率单位，工程内其他界面不要带额外单位。"),
        ("设置背景与材料", "Modeling/Bkg_Mat/Background.md", "背景材料、普通材料/色散材料等。"),
        ("设置计算区域", "Modeling/Design/Domain.md", "空气盒子/Domain 会影响精度、效率和资源消耗。"),
        ("建立几何模型", "Modeling/Modeling.md", "创建体、面、线并通过模型编辑调整。"),
        ("设置求解器与扫频", "Modeling/Design/Solver.md", "MFEM、基函数阶数、离散/插值/快速扫频。"),
        ("设置激励/端口", "Modeling/Stimulate/Wave_Port.md", "波端口、集总端口、点源、平面波、多导体与积分线。"),
        ("设置网格", "Mesh/3D_Mesh.md", "初始网格、局部加密、自适应网格、波端口网格。"),
        ("验证并运行仿真", "Simulation/Simulation.md", "验证、运行、停止、清除、运行波端口。"),
        ("查看结果与导出", "EM_Project/EM_Results.md", "端口结果、远场、快照、导出 Snp/图片。"),
    ]
    km = ["# 知识地图", "", "## 新手主线", ""]
    for i, (name, relp, desc) in enumerate(workflow_refs, 1):
        km.append(f"{i}. **{name}**：{desc} 来源：[{relp}](../10_extracted_pages/{relp})")
    km.extend(
        [
            "",
            "## Agent 问题类型到知识入口",
            "- “按钮在哪/有什么用”：`button_location_function_index.md` + 对应抽取页图片资源。",
            "- “怎么开始仿真”：`beginner_simulation_workflow.md`。",
            "- “扫频方法怎么选”：`simulation_methods_comparison.md`。",
            "- “端口怎么选/为什么建不了”：`ports_and_excitations.md` + 排错卡。",
            "- “报错/验证不过”：`troubleshooting_and_constraints.md`，并让用户提供完整日志。",
            "- “结果怎么看/怎么导出”：`post_processing_results.md`。",
        ]
    )
    write(INDEXES / "knowledge_map.md", "\n".join(km))

    btn_lines = [
        "# 按钮/入口/功能索引",
        "",
        "本索引从原始文档中抽取含“点击、右键、双击、工具栏、主菜单栏、按钮、图标”等描述的句子，用于回答“按钮在哪里、有什么用”。",
        "",
    ]
    seen = set()
    for module, label in sorted(DISPLAY_DIRS.items(), key=lambda kv: kv[1]):
        rows = [c for c in button_candidates if c["module"] == module]
        if not rows:
            continue
        btn_lines.append(f"## {label}")
        count = 0
        for c in rows:
            key = (c["title"], c["text"])
            if key in seen:
                continue
            seen.add(key)
            btn_lines.append(f'- **{c["title"]}**：{c["text"]} 来源：[{c["source"]}](../{c["source"]})')
            count += 1
            if count >= 45:
                break
        btn_lines.append("")
    write(INDEXES / "button_location_function_index.md", "\n".join(btn_lines))

    tr_lines = [
        "# 限制、注意与疑似故障原因索引",
        "",
        "本索引从帮助文档中抽取“必须、无法、不能、不可、不支持、注意、建议、检查、收敛、过大/过小”等语句。它不是完整报错库，但适合排查验证失败和仿真异常。",
        "",
    ]
    seen = set()
    for module, label in sorted(DISPLAY_DIRS.items(), key=lambda kv: kv[1]):
        rows = [c for c in constraints if c["module"] == module]
        if not rows:
            continue
        tr_lines.append(f"## {label}")
        count = 0
        for c in rows:
            key = (c["title"], c["text"])
            if key in seen:
                continue
            seen.add(key)
            tr_lines.append(f'- **{c["title"]}**：{c["text"]} 来源：[{c["source"]}](../{c["source"]})')
            count += 1
            if count >= 60:
                break
        tr_lines.append("")
    write(INDEXES / "constraint_warning_index.md", "\n".join(tr_lines))


def write_topics():
    write(
        TOPICS / "beginner_simulation_workflow.md",
        """# 新手仿真流程卡

## 最短流程

1. 新建或打开工程：从主页/文件入口创建工程，保存工程文件。
2. 设置单位：进入“建模 -> 设计 -> 单位”，确认长度、时间、频率单位。工程全局单位在这里统一设置，其他编辑界面不要额外带单位。
3. 设置材料与背景：确认普通材料、金属、色散材料等是否符合模型需求。
4. 设置计算区域：进入“设计 -> 计算区域”，确定空气盒子/Domain。计算区域直接影响精度、效率和资源消耗。
5. 建立几何：创建体、面、线，并用移动、旋转、布尔、拉伸、倒角等工具编辑。
6. 设置求解器和频率：确认求解器、基函数阶数、扫频范围和扫频方式。
7. 设置激励：按模型类型选择波端口、集总端口、点激励源或平面波。
8. 设置网格：先设置 3D 初始网格，必要时做局部加密；波端口可单独设置波端口网格。
9. 验证：在“仿真”中先点击“验证”，检查模型设置是否完整。
10. 运行：验证无误后点击“运行”。详细过程看日志窗口。
11. 后处理：在电磁结果中查看端口、快照、远场、接收器等结果，必要时导出 Snp 或图片。

## 验证失败时先查什么

- 是否设置了计算区域、频率、求解器、激励/端口。
- 端口是否满足几何/材料限制，例如波端口需贴在 Domain 上，集总端口面形状和接触方式有限制。
- 参数化扫描是否先在“变量”中定义了变量。
- 平面波是否满足背景材料、开放边界、离散扫频三项条件。
- 网格是否过密导致资源不足，或病态网格较多影响结果。
""",
    )
    write(
        TOPICS / "simulation_methods_comparison.md",
        """# 仿真方法对比卡

## 离散扫频

- 做法：利用当前网格剖分，逐点求解各频点电磁场。
- 优点：文档中说明为最准确的方法；适合关注各个频点场分布、频点数不多的情况。
- 缺点：速度较慢。
- 适用：结果有争议时可用离散方法复核；平面波源要求仿真方法仅限离散扫频。
- 来源：`10_extracted_pages/Modeling/Design/Frequency.md`、`10_extracted_pages/Modeling/Stimulate/Plane_Wave.md`

## 插值扫频

- 做法：在频率范围内由软件自动确定求解频点，再通过内插得到整个扫频范围响应。
- 关键参数：最大插值点数、插值误差。文档中默认最大插值点数为 250，默认插值误差为 1%。
- 收敛逻辑：满足插值误差或达到最大插值点数之一即结束；若达到最大插值点后误差仍大于目标，则结果不收敛。
- 注意：插值扫频频点由算法决定；应用插值扫频时，用户无法查看选定频点的 Snapshot。
- 来源：`10_extracted_pages/Modeling/Design/Frequency.md`

## 快速扫频

- 做法：基于降阶模型提升宽频带仿真速度。
- 优点：宽频带仿真建议优先采用。
- 关键参数：迭代次数表示降阶模型阶数，默认 100；一般越大越准确但更耗时。毫米波段建议 300，一般不要超过 500。
- 限制：平面波源目前不支持快速扫频。
- 来源：`10_extracted_pages/Modeling/Design/Frequency.md`

## 参数化扫描

- 做法：设置一个或多个设计参数的变化范围，软件自动生成一系列仿真任务。
- 前提：必须先在“变量”中添加变量；未设置变量的模型无法使用参数化扫描。
- 操作：仿真 -> 参数化扫描，选择变量、设置范围/步长/次数或任意点，添加到右侧并勾选后验证、开始。
- 默认参数选项：勾选“将默认参数设为一个参量”时，变量初始值会被加入扫描任务。
- 来源：`10_extracted_pages/Simulation/Parameter_Sweep.md`

## 自适应网格相关

- 自适应网格用于迭代改善网格和结果；详细日志中会显示迭代次数、残差、收敛数量、单元数、自由度和耗时。
- 残差越小，计算结果越接近真实值。
- 病态网格可通过显示网格定位，再在 3D 网格或自适应网格参数中调整。
- 来源：`10_extracted_pages/Tool/Details_logs.md`、`10_extracted_pages/Mesh/Show_Mesh.md`
""",
    )
    write(
        TOPICS / "ports_and_excitations.md",
        """# 端口与激励选择卡

## 波端口

- 用于模拟从端口进入或离开的电磁波模式。
- 波端口面的材料需为非金属。
- 当前文档说明只支持贴在 Domain 上的波端口，不支持不在 Domain 上的波端口。
- 端口名称只能为数字。
- 多导体终端形式的波端口必须选择一个导体作为参考导体，通常选共地导体。
- 来源：`10_extracted_pages/Modeling/Stimulate/Wave_Port.md`、`10_extracted_pages/Modeling/Stimulate/Multi_Conductors.md`

## 集总端口

- 用于模拟信号进入或离开设备的内部表面，常用于激励设备和测量 S 参数。
- 分为集总面端口和集总线端口。
- 集总面端口当前仅支持在圆环面和矩形面上建立，所在面材料由软件默认为空气，用户无法设置。
- 集总面端口仅支持上下边接触金属结构，不可经过金属体截面。
- 可使用集总面端口时建议优先使用；无法建立面端口时再考虑集总线端口。
- 集总线端口路径不可完全位于模型外边界，不可完全贴着空气盒子。
- 端口阻抗必须是大于零的实数，默认 50 Ω。
- 来源：`10_extracted_pages/Modeling/Stimulate/Lumped_Port.md`

## 点激励源

- 适合模拟从单点或局部位置发射的电磁波。
- 与波端口、集总面端口、平面波不同，通常用于难以用面激励表达的复杂结构。
- WavEDA 仅支持快速扫频和离散扫频时添加点激励源进行计算。
- 点源形式包括电偶极子和磁偶极子。
- 来源：`10_extracted_pages/Modeling/Stimulate/Create_Point_Source.md`

## 平面波

- 用于模拟来自远处的外部电磁波入射。
- 必须满足：背景材料为普通材料而不是导电材料；边界条件为开放边界；仿真方法仅限离散扫频。
- 传播方向不可输入 `(0,0,0)`。
- 频域仿真时参考频率不可填写。
- 椭圆极化用长半轴/短半轴电场定义时，长半轴电场必须大于短半轴电场。
- 来源：`10_extracted_pages/Modeling/Stimulate/Plane_Wave.md`
""",
    )
    write(
        TOPICS / "troubleshooting_and_constraints.md",
        """# 排错与约束卡

## 先看哪里

- “仿真 -> 验证”后，下方日志会给出报错或警告，优先按日志提示检查模型设置。
- “工具 -> 详细日志”可查看网格密度、自由度、仿真时间、自适应网格迭代、残差、收敛数量和每个物体的网格数量。
- “网格 -> 显示网格 -> 病态”可定位网格质量较差区域，再做局部加密或调整自适应网格参数。

## 常见问题到检查项

| 现象/问题 | 优先检查 | 相关来源 |
|---|---|---|
| 参数化扫描无法使用 | 是否已在“变量”中添加变量 | `Simulation/Parameter_Sweep.md` |
| 平面波无法仿真或验证失败 | 背景材料是否普通材料、边界是否开放、扫频是否离散 | `Modeling/Stimulate/Plane_Wave.md` |
| 波端口建不了/结果异常 | 端口面是否非金属、是否贴在 Domain 上、名称是否为数字 | `Modeling/Stimulate/Wave_Port.md` |
| 集总面端口建不了 | 面是否为圆环面或矩形面，是否上下边接触金属，是否穿过金属截面 | `Modeling/Stimulate/Lumped_Port.md` |
| 集总线端口异常 | 路径是否完全位于模型外边界/空气盒子上 | `Modeling/Stimulate/Lumped_Port.md` |
| 网格数量爆炸/仿真很慢 | 局部网格尺寸是否设置过小，扫频点数是否过多，基函数阶数是否过高 | `Mesh/3D_Mesh.md`、`Modeling/Design/Frequency.md`、`Modeling/Design/Solver.md` |
| 结果不收敛 | 插值误差目标是否过小、最大插值点数是否不足、病态网格是否较多 | `Modeling/Design/Frequency.md`、`Mesh/Show_Mesh.md` |
| 停止仿真很慢 | 文档说明有些模型停止时间较长，可看日志右下角进度条 | `Simulation/Simulation.md` |
| 变量定义失败/冲突 | 变量名不区分大小写，`pi`、`e`、`t`、`t1`、`t2` 已被软件定义，不能再次定义 | `Tool/Variables.md` |
| 单位输入异常 | 单位在“单位”界面全局设置，其他界面编辑时不能带额外单位 | `Modeling/Design/Unit.md` |

## 第一版缺口

原始帮助文档没有提供完整“错误码/报错文本 -> 原因 -> 解决方案”表。后续建议把真实日志按模板补充到 `90_maintenance_templates/error_case_template.md`，形成 `40_error_cases/`。

更多自动抽取的限制语句见：`20_indexes/constraint_warning_index.md`。
""",
    )
    write(
        TOPICS / "post_processing_results.md",
        """# 后处理与结果查看卡

## 电磁结果入口

仿真结束后，可在工程树“电磁结果”中查看接收器、端口、快照和远场结果。

## 端口结果

- 右键端口结果可新建端口结果、新建史密斯圆图、导出 Snp、删除所有结果。
- 新建端口结果可查看 S 参数、差分对、Z 参数、TDR、TDT、电压、电流等；波端口还可查看 Y 参数、线阻抗和 Gamma。
- 可通过添加曲线选择单位并绘制目标端口结果。
- 来源：`10_extracted_pages/EM_Project/EM_Results.md`、`10_extracted_pages/Post_Processing/New_Port.md`

## 远场结果

- 仿真前需要进行远场设置。
- 仿真完成后可查看接收功率、辐射功率、辐射效率、总效率、单站 RCS、平均功率、轴比、轴比-频率曲线、远场 3D/2D/1D 增益图等。
- 平面波仿真可查看单站雷达散射截面曲线。
- 来源：`10_extracted_pages/EM_Project/Far_field.md`、`10_extracted_pages/EM_Project/EM_Results.md`

## 接收器结果

- 接收器仿真只能在离散或快速扫频下进行。
- 仿真完成后可以再新建接收器查看结果，但需要在工具栏“设计设置”中选择保存结果。
- 来源：`10_extracted_pages/Post_Processing/New_Observers.md`

## 导出

- 可导出图片和 Snp 文件。
- 图表设置中改变 X 轴范围只改变显示，导出数据时仍导出全范围 X 轴数据。
- 来源：`10_extracted_pages/Tool/Export_Figure.md`、`10_extracted_pages/Tool/Export_Snp.md`、`10_extracted_pages/Post_Processing/New_Port.md`
""",
    )


def write_templates():
    write(
        TEMPLATES / "error_case_template.md",
        """# 报错案例补充模板

复制本模板到 `40_error_cases/` 后填写。建议文件名：`错误关键词_场景.md`。

## 报错原文

```text
粘贴完整报错/警告/日志原文。
```

## 出现位置

- 操作阶段：建模 / 端口 / 网格 / 验证 / 运行 / 后处理 / 导出
- 触发操作：
- WavEDA 版本：
- 模型类型：

## 可能原因

1. 
2. 
3. 

## 解决步骤

1. 
2. 
3. 

## 验证方式

- 修复后如何判断问题消失：
- 是否需要重新剖分网格：
- 是否需要重新运行端口/全模型：

## 关联知识

- 相关抽取页：
- 相关截图路径：
- 相关用户案例：
""",
    )
    write(
        TEMPLATES / "button_entry_template.md",
        """# 按钮/入口补充模板

## 按钮或入口名称


## 所在位置

- 主菜单：
- 工具栏：
- 工程树：
- 右键菜单：
- 对话框：

## 功能作用


## 操作步骤

1. 
2. 
3. 

## 参数说明

| 参数 | 含义 | 推荐/限制 |
|---|---|---|
| | | |

## 常见误区

- 

## 来源

- 文档页：
- 截图路径：
""",
    )
    write(
        TEMPLATES / "beginner_task_flow_template.md",
        """# 新手任务流程补充模板

## 任务目标

例如：创建一个微带线模型并查看 S 参数。

## 适用用户


## 前置条件

- 

## 操作流程

1. 
2. 
3. 

## 参数建议

| 参数 | 建议值 | 原因 |
|---|---|---|
| | | |

## 预期结果


## 常见问题

| 问题 | 原因 | 解决 |
|---|---|---|
| | | |

## 关联文档

- 
""",
    )


def main():
    records, by_module, constraints, button_candidates = extract_pages()
    write_readme(records, by_module)
    write_agent_guide()
    write_indexes(records, by_module, constraints, button_candidates)
    write_topics()
    write_templates()

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_root": str(DOC_ROOT),
        "output_root": str(OUT),
        "html_pages": len(records),
        "modules": {m: len(v) for m, v in sorted(by_module.items())},
        "constraint_sentences": len(constraints),
        "button_sentences": len(button_candidates),
    }
    write(OUT / "_generation_summary.json", json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
