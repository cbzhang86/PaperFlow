# 🛠️ Paperflow

这是 Claude Code 的项目定义文件。操作指令和完整文档在 [`AGENTS.md`](AGENTS.md) 中。

Paperflow 是一个 CLI 技能集，用于学术文献管理和 AI 辅助论文写作。通过 `KNOWLEDGE_ROOT` 环境变量指向本地知识库数据目录。

---

## 快速开始

```bash
# 查看状态（新对话第一步）
python skills/pipeline.py status

# 初始化
python skills/global_config.py init --backend filesystem

# 采集论文
python skills/collect/search.py "关键词" --direction 方向名 --limit 3

# 一键跨篇沉淀
python skills/extract/regenerate.py --dir .

# 生成报告
python skills/report/daily.py
python skills/report/weekly.py
```

---

## 项目约定

- 所有脚本使用 Python 3.11+，中文注释
- 去重使用本地 SQLite，归档使用本地文件系统
- 精读报告 175-205 行，7 维评分每维必须有评价性理由
- 统计量必须有真实来源，不得虚构

完整文档见 [`AGENTS.md`](AGENTS.md)。
