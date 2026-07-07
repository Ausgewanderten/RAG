# WavEDA + 多物理场笔记 RAG 使用说明

## 项目位置

所有产出都在：

```text
D:\RAGGG
```

本项目读取两个资料源：

```text
D:\Program Files (x86)\documentation\helpHtml
D:\暑期实践\多物理场仿真知识库
```

读取过程不会修改这两个原始资料目录。

## 构建知识库

在 `D:\RAGGG` 中运行：

```powershell
.\.venv\Scripts\python.exe scripts\build_knowledge_base.py
```

成功后会生成：

```text
D:\RAGGG\data\raw_manifest.json
D:\RAGGG\data\processed_chunks.json
D:\RAGGG\data\index\chunks.json
D:\RAGGG\data\index\vectors.npy
```

## 启动桌面应用

在 `D:\RAGGG` 中运行：

```powershell
py -3 app\desktop_app.py
```

启动脚本会自动切换到 `D:\RAGGG\.venv` 中的 PySide6 环境。

桌面窗口包含：

- 左侧：知识库状态、重建按钮、重新载入按钮。
- 中间：中文问答区。
- 右侧：来源片段、来源类型、路径和匹配分数。

## 验收测试

运行自动测试：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

运行三条 smoke 问题：

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test.py
```

当前 smoke 问题包括：

- 波端口怎么设置？
- 什么是 Maxwell 方程组？
- WavEDA 里的 PML 和吸收边界有什么关系？

## WavEDA 优先规则

本项目把 WavEDA 作为最重要的资料源：

- 问题涉及 WavEDA、端口、边界、PML、网格、仿真、设置等软件语境时，优先返回 WavEDA 帮助文档。
- Obsidian 笔记作为理论补充，用来解释吸收边界、Maxwell 方程、有限元等背景。
- 纯理论问题会优先使用 Obsidian 中更直接的定义或公式笔记。

## 模型配置

未配置 API Key 时，系统仍可本地检索并返回来源片段式回答。

如果要调用 OpenAI 兼容接口，可以复制 `.env.example` 为 `.env`，填写：

```text
RAG_LLM_BASE_URL=https://api.deepseek.com
RAG_LLM_API_KEY=你的密钥
RAG_LLM_MODEL=deepseek-chat
```

## 当前限制

第一版使用本地哈希向量和关键词混合检索，不依赖模型下载，稳定但语义能力弱于真正的 embedding 模型。后续可以在不改变项目结构的情况下替换为 BGE、FAISS 或其他向量模型。
