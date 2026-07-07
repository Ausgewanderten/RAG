# WavEDA 与多物理场笔记 RAG 桌面系统设计

## 背景

本项目在 `D:\RAGGG` 中新建一个独立的桌面版 RAG 系统。系统合并两类资料：

- WavEDA 帮助文档：`D:\Program Files (x86)\documentation\helpHtml`
- 多物理场 Obsidian 笔记：`D:\暑期实践\多物理场仿真知识库`

旧项目 `D:\暑期实践\RAG系统` 只作为设计和实现参考，不直接修改，不把本次产出写回旧项目。

## 目标

系统需要完成以下事情：

- 读取 WavEDA HTML 帮助文档和 Obsidian Markdown 笔记。
- 清洗并保留中文正文、标题层级、公式、链接、图片说明、Obsidian `[[wikilinks]]`。
- 生成统一知识库，能够区分资料来源。
- 构建本地向量索引和可复查的 chunk 文件。
- 提供桌面窗口应用，用中文进行问答。
- 每次回答展示引用来源、来源类型、文件路径、标题和片段。
- 支持 OpenAI 兼容的模型接口，默认沿用 DeepSeek 这类兼容服务的配置方式。
- 所有项目产出放在 `D:\RAGGG`。

## 非目标

本阶段不做以下事情：

- 不修改 `D:\暑期实践\RAG系统`。
- 不修改 WavEDA 原始帮助文档目录。
- 不修改 Obsidian 原始笔记内容。
- 不做联网爬取。
- 不把知识库同步回 Obsidian。
- 不强制建立 Web 前端；桌面应用是主交付形态。

## 项目结构

计划在 `D:\RAGGG` 下形成以下结构：

```text
D:\RAGGG
  app\
    desktop_app.py
  data\
    raw_manifest.json
    processed_chunks.json
    index\
      chunks.json
      vectors.npy
      index.faiss
  docs\
    superpowers\
      specs\
    progress\
    user_guide.md
  scripts\
    build_knowledge_base.py
    smoke_test.py
  src\
    config.py
    loaders\
      html_loader.py
      markdown_loader.py
    preprocessing\
      cleaner.py
      chunker.py
    indexing\
      embeddings.py
      vector_store.py
    retrieval\
      retriever.py
      reranker.py
    generation\
      llm_client.py
      prompt_builder.py
    pipeline\
      rag_pipeline.py
    desktop\
      main_window.py
      workers.py
  tests\
  .env.example
  requirements.txt
  README.md
```

`index.faiss` 作为可选缓存；在 Windows 中文路径下，`vectors.npy` 和 `chunks.json` 是更可靠的权威索引状态。

## 数据模型

每个知识块使用统一结构：

```json
{
  "id": "stable chunk id",
  "source_type": "waveda_help | obsidian_note",
  "source_path": "absolute file path",
  "relative_path": "path relative to source root",
  "title": "page or note title",
  "section": "nearest heading",
  "content": "cleaned chunk text",
  "links": ["linked pages or wikilinks"],
  "images": ["image path or caption when available"],
  "metadata": {
    "domain": "waveda | multiphysics",
    "content_type": "help_page | note",
    "has_formula": true,
    "has_wikilink": true
  }
}
```

稳定 ID 由来源类型、相对路径、标题层级和 chunk 序号生成，便于后续增量更新。

## 读取与清洗

HTML 读取规则：

- 从 `helpHtml` 递归读取 `.html` 和 `.htm`。
- 使用 HTML 解析器提取 `title`、`h1` 至 `h6`、段落、列表、表格文字、链接文字和图片说明。
- 保留 WavEDA 内部页面链接，转换成可读路径。
- 过滤导航样式、CSS、脚本和重复模板文字。

Markdown 读取规则：

- 从 Obsidian 知识库递归读取 `.md`。
- 保留标题、正文、代码块、公式、表格和 `[[wikilinks]]`。
- 跳过明显的 Obsidian 配置目录和非正文附件。
- 图片链接保留为引用信息，不把二进制图片直接嵌入向量文本。

## 切块策略

切块以标题层级和段落为主，避免把不同主题混在一起：

- 目标 chunk 长度约 500 至 900 个中文字符。
- 超长段落按句子边界拆分。
- 公式所在段落尽量与解释文字放在同一个 chunk。
- 页面标题、章节标题和来源信息会进入检索上下文，但不重复污染正文。
- WavEDA 操作步骤类页面优先保留有序列表顺序。

## 检索策略

检索使用混合方法：

- 向量检索：处理语义近似问题。
- 关键词检索：处理 WavEDA 菜单名、按钮名、英文术语、文件名。
- 元数据加权：问题包含 WavEDA、端口、边界、网格、仿真时提高 `waveda_help` 权重；问题偏理论、公式、教材概念时提高 `obsidian_note` 权重。
- 公式问题加权：含“公式、方程、推导、Maxwell、边界条件”等词时优先包含实际公式证据的 chunk。

默认返回 6 至 8 个候选片段给生成模块。

## 生成策略

回答使用 OpenAI 兼容接口。配置放在 `.env` 中：

```text
RAG_LLM_BASE_URL=https://api.deepseek.com
RAG_LLM_API_KEY=...
RAG_LLM_MODEL=...
```

生成要求：

- 默认中文回答。
- 先基于检索片段作答，不随意编造。
- 资料不足时明确说明缺少依据。
- 引用来源放在回答末尾，显示标题、来源类型、路径和片段编号。
- 对 WavEDA 操作问题，优先给具体步骤。
- 对理论问题，优先给定义、公式、物理意义和与软件设置的联系。

## 桌面应用

桌面应用采用 Qt Widgets 风格，主界面分为三块：

- 左侧：会话历史和索引状态。
- 中间：聊天问答区。
- 右侧：来源列表，展示标题、来源类型、路径、匹配片段和相似度。

底部状态栏显示：

- 知识库是否已构建。
- chunk 数量。
- 当前模型配置是否完整。
- 最近一次构建时间。

应用启动时不自动改动源文档。用户可以通过按钮触发“重建知识库”。如果后续需要自动同步，可以在桌面应用运行时增加定时扫描，但第一版以手动重建为主，降低误操作风险。

## 配置

`.env.example` 提供以下配置：

```text
WAVEDA_HELP_ROOT=D:\Program Files (x86)\documentation\helpHtml
OBSIDIAN_VAULT_ROOT=D:\暑期实践\多物理场仿真知识库
RAG_DATA_DIR=D:\RAGGG\data
RAG_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
RAG_LLM_BASE_URL=https://api.deepseek.com
RAG_LLM_API_KEY=
RAG_LLM_MODEL=deepseek-chat
```

如果用户没有填写 API Key，系统仍能构建索引和检索来源，但不能生成完整模型回答。

## 测试与验收

需要完成以下验证：

- 能成功读取 WavEDA HTML 页面，至少识别 `Introduction.html`、`Boundary.html`、`Wave_Port.html`。
- 能成功读取 Obsidian Markdown 笔记，保留公式和 `[[wikilinks]]`。
- 构建后生成 `data\processed_chunks.json`、`data\index\chunks.json`、`data\index\vectors.npy`。
- 桌面应用能启动。
- 提问“波端口怎么设置？”时，能返回 WavEDA 来源。
- 提问“什么是 Maxwell 方程组？”时，能返回 Obsidian 理论来源。
- 提问“WavEDA 里的 PML 和吸收边界有什么关系？”时，能同时利用两类来源。
- 无答案时能说“资料中没有足够依据”，而不是编造。

## 风险与处理

- Windows 中文路径可能导致 FAISS 原生缓存写入失败：以 `vectors.npy` 和 `chunks.json` 为权威状态，`index.faiss` 只作为可选缓存。
- HTML 页面可能有大量模板文字：清洗阶段过滤重复 header、样式和导航。
- WavEDA 操作页面和理论笔记可能术语不同：检索阶段用关键词和元数据加权补偿。
- 模型 API 配置可能缺失：桌面端显示清晰状态，允许只做检索预览。
- Obsidian 笔记有部分页面可能是学习计划而不是正文：公式和实质内容问题优先包含真实公式、定义和解释的 chunk。

## 实施顺序

1. 建立项目骨架和配置文件。
2. 实现 HTML 与 Markdown 读取器。
3. 实现清洗、切块和元数据生成。
4. 生成知识库和索引文件。
5. 实现检索和回答管线。
6. 实现桌面窗口。
7. 添加测试和 smoke test。
8. 写 README、用户指南和进度记录。

## 验收结果记录

实现完成后，在 `D:\RAGGG\docs\progress` 写入本次构建记录，包含：

- 数据源路径。
- 页面和笔记数量。
- chunk 数量。
- 验证问题和结果摘要。
- 启动方式。
- 已知限制。
