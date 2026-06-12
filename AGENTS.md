# PaperFlow — 项目指令

PaperFlow 是一个 CLI 技能集，用于学术文献管理和 AI 辅助论文写作。通过 `KNOWLEDGE_ROOT` 环境变量指向本地知识库数据目录，所有操作在数据目录下执行。

---

## 环境变量

- `KNOWLEDGE_ROOT` — 必需。指向知识库根目录（应包含 `01_论文原文/`、`02_精读报告/`、`config/` 等子目录）。
- 未设置时默认使用当前工作目录。

---

## 工作流程

### 1. 查看状态（开始新对话时第一步）

```bash
python skills/pipeline.py status
```

### 2. 初始化（首次使用）

```bash
python skills/global_config.py init --backend filesystem
```

### 3. 日常流程

**采集论文**：
```bash
python skills/collect/search.py "关键词" --direction 方向名 --limit 3
```

**撰写精读报告**：按 `templates/reading-report.md` 模板逐篇分析。

**生成跨篇沉淀**：
```bash
python skills/extract/regenerate.py --dir .
```

**生成报告**：
```bash
python skills/report/daily.py
python skills/report/weekly.py
python skills/report/monthly.py
```

### 4. 论文写作

```bash
# 生成审稿背景知识包
python skills/ars_bridge.py stage-3 --topic "主题" --paper "论文名"

# 引文审计
python skills/ars_bridge.py stage-5 --refs "引文1,引文2" --paper "论文名"

# 格式化终稿
python skills/report/create_formatted_docx.py convert -i 终稿.md -o 终稿.docx --style 学报
```

---

## 目录结构约定

```
{KNOWLEDGE_ROOT}/
├── 01_论文原文/      # PDF 文件（按方向分目录）
├── 02_精读报告/      # v10 格式精读分析
├── 03_学术写作素材库/ # 跨篇沉淀（自动生成）
├── config/           # YAML 配置
└── ...               # 其他可选目录
```

`01_论文原文/` 和 `02_精读报告/` 下的方向子目录应保持一致。

---

## 编码约定

- 所有脚本使用 Python 3.11+
- 中文注释，函数有 docstring
- 脚本统一接口：`python script.py <action> <args>`
- stdout 输出操作结果，stderr 输出日志

---

## 操作安全规则

1. **PDF 操作**：下载前先查重（dedup），归档前验证文件完整性（`%PDF` 魔术字检查）
2. **精读报告**：每篇 175-205 行，7 维评分每维必须有评价性理由
3. **归档输出**：每个阶段产出必须完整写入文件，不准写摘要版
4. **统计量**：必须有真实计算过程或明确来源，不得虚构
