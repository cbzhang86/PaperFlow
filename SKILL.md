---
name: PaperFlow
description: 学术文献管理与AI论文写作工作流框架 — 采集、精读、跨篇沉淀、ARS论文写作
version: 10.5.0
user-invocable: true
emoji: 🛠️
homepage: https://github.com/cbzhang86/PaperFlow
requires:
  env:
    - KNOWLEDGE_ROOT
  bins:
    - python3
---
# 学术知识工作流框架

一个可移植的 CLI 管线，用于学术文献管理和 AI 辅助论文写作。**零外部服务依赖**，Clone 即用，替换关键词即可适配任何学科。

---

## 环境变量

| 变量 | 必需 | 说明 |
|:-----|:----:|:------|
| `KNOWLEDGE_ROOT` | 是 | 指向你的知识库数据目录（含 `01_论文原文/`、`02_精读报告/` 等子目录）|
| `SKILLS_DIR` | 否 | 指向 framework 的 `skills/` 目录（默认与 `SKILL.md` 同级）|

如果未设置 `SKILLS_DIR`，脚本会从 `SKILL.md` 所在目录向上查找 `skills/`。

---

## 管线流程

### 第 1 步：采集

多源搜索并下载论文 PDF，自动去重（SQLite MD5 指纹），自动命名（年份_作者_标题.pdf）。

```bash
python skills/collect/search.py "关键词" --direction 方向名 --limit 3
```

支持的源：**arXiv**（英文预印本）、**OpenAlex**（开放索引）、**ncpssd**（中文 CSSCI，需 Edge CDP）。

### 第 2 步：精读

按 v10 模板逐篇分析论文，175-205 行，含 7 维评分 + 我的思考。

```bash
python skills/review/draft.py 论文.pdf    # 自动起草
python skills/review/check.py 精读报告.md  # 合规检查
```

### 第 3 步：跨篇沉淀

一键扫描全部精读报告，自动提取摘要、理论框架、关键论点、研究空白。

```bash
python skills/extract/regenerate.py --dir .
```

### 第 4 步：报告

```bash
python skills/report/daily.py     # 日报
python skills/report/weekly.py    # 周报
python skills/report/monthly.py   # 月报
```

### 第 5 步：论文写作（ARS 集成）

通过知识注入管线与 academic-research-skills 集成：

```bash
# 生成知识包（注入到 ARS 各阶段）
python skills/ars_bridge.py stage-3 --topic "主题" --paper "论文名"
python skills/ars_bridge.py stage-5 --refs "引文1,引文2" --paper "论文名"

# 格式化终稿
python skills/report/create_formatted_docx.py convert \
  -i 终稿.md -o 终稿_学报版.docx --style 学报
```

---

## 关键设计

### 统一去重引擎
所有论文去重使用本地 SQLite，不论归档后端选什么。

```bash
python skills/metadata/dedup.py rebuild   # 全量重建
python skills/metadata/dedup.py status    # 查看统计
```

### 插件式归档后端
内置 filesystem（零依赖）和 zotero（可选）。放在 `metadata/backends/` 下自动发现。

### 多 Agent 角色
每个 Agent = prompt 模板 + Skill 调用规则，可移植到任何 AI 工具。

| Agent | 职责 |
|:------|:------|
| 采集Agent | 搜索 → 去重 → 下载 → 归档 |
| 精读Agent | 读 PDF → 写精读 → 自查 |
| 审稿Agent | 审核报告 → 7 维评分 |
| 综合Agent | 跨篇对比 → 发现空白 |
| 运维Agent | 完整性检查 → Obsidian 同步 |

---

## 换领域指南

改一个文件即可换领域：

```yaml
# config/areas.yaml
areas:
  计算机科学:
    keywords: ["deep learning", "transformer"]
    sources: ["arxiv", "openalex"]
```

首次运行 `python skills/global_config.py init` 交互式选择归档后端。

---

## AGENTS.md

本技能的工作指令和项目约定见 `AGENTS.md`。
