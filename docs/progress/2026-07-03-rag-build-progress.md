# 2026-07-03 RAG 构建进度记录

## 已完成

- 在 `D:\RAGGG` 中创建独立 RAG 项目。
- 保留设计文档：`docs\superpowers\specs\2026-07-03-waveda-obsidian-rag-design.md`。
- 保留实施计划：`docs\superpowers\plans\2026-07-03-waveda-obsidian-rag.md`。
- 实现 HTML 帮助文档读取器。
- 实现 Obsidian Markdown 笔记读取器。
- 实现清洗、切块、来源元数据和 chunk ID。
- 实现本地哈希向量索引。
- 实现混合检索和 WavEDA 优先排序。
- 实现无 API Key 时的本地引用式回答。
- 实现桌面窗口入口：`app\desktop_app.py`。
- 桌面窗口已升级为 PySide6 深色高级工作台界面。
- 实现真实知识库构建脚本：`scripts\build_knowledge_base.py`。
- 实现 smoke 验证脚本：`scripts\smoke_test.py`。

## 数据源

```text
WavEDA 帮助文档：D:\Program Files (x86)\documentation\helpHtml
Obsidian 笔记：D:\暑期实践\多物理场仿真知识库
```

## 构建结果

最近一次构建结果：

```text
documents=201
waveda_documents=97
obsidian_documents=104
chunks=1408
data_dir=D:\RAGGG\data
```

生成文件：

```text
D:\RAGGG\data\raw_manifest.json
D:\RAGGG\data\processed_chunks.json
D:\RAGGG\data\index\chunks.json
D:\RAGGG\data\index\vectors.npy
```

## 验证结果

通过的自动测试：

```text
18 tests passed
```

通过的 smoke 问题：

- `波端口怎么设置？`：首要来源为 `waveda_help | Modeling/Stimulate/Wave_Port.html`。
- `什么是 Maxwell 方程组？`：首要来源为 `obsidian_note | 01-基础概念/Maxwell方程组是什么.md`。
- `WavEDA 里的 PML 和吸收边界有什么关系？`：首要来源为 `waveda_help | EM_Project/Boundary.html`，并补充 Obsidian 中吸收边界理论笔记。

## WavEDA 优先调整

根据用户强调“WavEDA 是最重要的”，检索规则已设置为：

- WavEDA 软件语境优先 WavEDA 帮助页。
- PML、边界、端口、网格、仿真等问题优先匹配 WavEDA 文档。
- 理论笔记作为补充材料，不在软件操作问题中压过 WavEDA 帮助页。

## 启动方式

构建知识库：

```powershell
.\.venv\Scripts\python.exe scripts\build_knowledge_base.py
```

启动桌面应用：

```powershell
py -3 app\desktop_app.py
```

运行验证：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\smoke_test.py
```
