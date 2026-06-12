#!/usr/bin/env python3
"""日报/周报/月报生成器 v2 — 读精读报告内容，产出有信息量的报告"""
import sys, os, re, json
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime, date, timedelta
from pathlib import Path
from collections import defaultdict

try:
    from _config import PROJECT_ROOT, DIRS
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from global_config import PROJECT_ROOT, DIRS

REPORT_DIR = DIRS["02_reports"]
PDF_DIR = DIRS["01_raw"]
MATER_DIR = DIRS["03_materials"]
OUTPUT_DIR = DIRS["05_reports"]
OUTPUT_DIR.mkdir(exist_ok=True)

def read_frontmatter(content):
    """提取YAML frontmatter为字典"""
    if not content.startswith('---'): return {}
    end = content.find('---', 3)
    if end < 0: return {}
    fm = {}
    for line in content[3:end].strip().split('\n'):
        if ':' in line:
            key, _, val = line.partition(':')
            fm[key.strip()] = val.strip().strip("'\"").strip()
    return fm

def get_section(content, section_name):
    """提取精读报告中的段落"""
    for p in ['### ' + section_name, '## ' + section_name]:
        s = content.find(p)
        if s >= 0:
            rest = content[s+len(p):]
            end_list = []
            for m in ['\n### ', '\n## ', '\n---\n']:
                pos = rest.find(m, 10)
                if pos > 0: end_list.append(pos)
            end = min(end_list) if end_list else len(rest)
            text = rest[:end].strip()
            # 取前200字
            first_para = text.split('\n\n')[0] if '\n\n' in text else text
            return first_para[:200]
    return ''

def today_reports(target_date):
    """获取指定日期的精读报告（按mtime）"""
    results = []
    start = datetime(target_date.year, target_date.month, target_date.day)
    end = start + timedelta(days=1)
    for area_dir in REPORT_DIR.iterdir():
        if not area_dir.is_dir(): continue
        for f in area_dir.glob("*_精读报告.md"):
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if start <= mtime < end:
                with open(f, 'r', encoding='utf-8', errors='replace') as fh:
                    content = fh.read()
                fm = read_frontmatter(content)
                finding = get_section(content, '核心发现')
                thinking = get_section(content, '我的思考')
                results.append({
                    'area': area_dir.name,
                    'file': f.name,
                    'title': fm.get('title', f.stem),
                    'author': fm.get('author', ''),
                    'score': fm.get('score', ''),
                    'method': fm.get('methodology', ''),
                    'finding': finding[:150],
                    'thinking_first': thinking.split('\n')[0] if thinking else '',
                })
    return results

def count_area_reports():
    """统计各方向精读数量"""
    counts = {}
    for area_dir in REPORT_DIR.iterdir():
        if not area_dir.is_dir(): continue
        n = len(list(area_dir.glob("*_精读报告.md")))
        n_pdf = 0
        pdf_dir = PDF_DIR / area_dir.name
        if pdf_dir.exists():
            n_pdf = len(list(pdf_dir.glob("*.pdf")))
        counts[area_dir.name] = {'reports': n, 'pdfs': n_pdf}
    return counts

def get_theory_gaps(area):
    """从素材库获取某方向的研究空白数量"""
    gap_file = MATER_DIR / '研究空白' / f'{area}_研究空白.md'
    if gap_file.exists():
        with open(gap_file, 'r', encoding='utf-8') as fh:
            content = fh.read()
        # 统计 ### 标题 行数
        topics = len(re.findall(r'^### ', content, re.MULTILINE))
        return topics
    return 0

# =========================================================================
# 日报
# =========================================================================
def generate_daily(target_date=None):
    target = target_date or date.today()
    date_str = target.strftime("%Y-%m-%d")
    reports = today_reports(target)
    counts = count_area_reports()

    lines = [
        f'# {date_str} 知识库日报',
        f'> 生成: {datetime.now().strftime("%H:%M")}',
        '',
        '## 📊 今日概况',
        '',
        f'- 今日完成精读: **{len(reports)}** 篇',
    ]
    total_rpt = sum(c['reports'] for c in counts.values())
    total_pdf = sum(c['pdfs'] for c in counts.values())
    lines.append(f'- 累计精读: **{total_rpt}** / **{total_pdf}** PDF')
    lines.append('')

    if reports:
        lines.append('## 📖 今日精读')
        lines.append('')
        for r in reports:
            score_str = f' ⭐{r["score"]}' if r['score'] else ''
            lines.append(f'### {r["title"]}{score_str}')
            lines.append(f'> {r["author"]} | {r["area"]} | 方法: {r["method"][:40]}')
            lines.append('')
            if r['finding']:
                lines.append(f'**核心发现**: {r["finding"]}')
                lines.append('')
            if r['thinking_first']:
                lines.append(f'**我的思考**: {r["thinking_first"]}')
                lines.append('')
            lines.append('---')
            lines.append('')
    else:
        lines.append('> 无新增精读。')
        lines.append('')

    # 各方向进度
    lines.append('## 📈 各方向进度')
    lines.append('')
    lines.append('| 方向 | 精读/PDF | 缺口 | 状态 |')
    lines.append('|------|:--------:|:----:|:----:|')
    for area in ['公共管理学', '社会学', '老龄化', '青少年研究', '交叉研究']:
        c = counts.get(area, {'reports':0, 'pdfs':0})
        gap = c['pdfs'] - c['reports']
        status = '✅' if gap <= 0 else f'⚠️缺{gap}'
        lines.append(f'| {area} | {c["reports"]}/{c["pdfs"]} | {gap} | {status} |')
    lines.append('')

    # 明日计划提示
    lines.append('## 📋 明日计划')
    lines.append('')
    # 找缺口最大的方向
    gaps = [(a, c['pdfs']-c['reports']) for a, c in counts.items()]
    gaps.sort(key=lambda x: -x[1])
    for area, gap in gaps:
        if gap > 0:
            lines.append(f'- [ ] **{area}**: 还有 {gap} 篇PDF未精读（优先）')
    lines.append('- [ ] 更新进度看板')
    lines.append('')

    content = '\n'.join(lines)
    fp = OUTPUT_DIR / f'日报_{date_str}.md'
    fp.write_text(content, encoding='utf-8')
    print(f'[OK] 日报_{date_str}.md ({len(reports)}篇)')

# =========================================================================
# 周报
# =========================================================================
def generate_weekly(target_date=None):
    target = target_date or date.today()
    week_start = target - timedelta(days=target.weekday())
    counts = count_area_reports()

    # 本周的工作量 = 当前总量 - 上周六的快照（此处简化，用mtime统计）
    week_reports = []
    cutoff = datetime(week_start.year, week_start.month, week_start.day)
    for area_dir in REPORT_DIR.iterdir():
        if not area_dir.is_dir(): continue
        for f in area_dir.glob("*_精读报告.md"):
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime >= cutoff:
                with open(f, 'r', encoding='utf-8') as fh:
                    content = fh.read()
                fm = read_frontmatter(content)
                week_reports.append({
                    'area': area_dir.name,
                    'title': fm.get('title', f.stem),
                    'score': fm.get('score', ''),
                    'method': fm.get('methodology', ''),
                })

    total_rpt = sum(c['reports'] for c in counts.values())
    total_pdf = sum(c['pdfs'] for c in counts.values())

    lines = [
        f'# {week_start.strftime("%Y-%m-%d")} 周报',
        f'> 周期: 本周 | 生成: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
        '',
    ]

    # 本周概览
    lines.append('## 📊 本周概览')
    lines.append('')
    lines.append(f'- 本周完成精读: **{len(week_reports)}** 篇')
    lines.append(f'- 累计: **{total_rpt}** 篇精读 / **{total_pdf}** 篇PDF')
    lines.append('')

    # 各方向对比
    lines.append('## 📈 各方向进展')
    lines.append('')
    lines.append('| 方向 | 精读 | PDF | 缺口 | 研究空白 | 状态 |')
    lines.append('|------|:---:|:---:|:----:|:--------:|:----:|')
    for area in ['公共管理学', '社会学', '老龄化', '青少年研究', '交叉研究']:
        c = counts.get(area, {'reports':0, 'pdfs':0})
        gap = c['pdfs'] - c['reports']
        gaps_n = get_theory_gaps(area)
        status = '✅' if gap <= 0 else '⚠️'
        lines.append(f'| {area} | {c["reports"]} | {c["pdfs"]} | {gap} | {gaps_n}处 | {status} |')
    lines.append('')

    # 本周精读
    if week_reports:
        lines.append('## 📖 本周精读')
        lines.append('')
        methods_seen = defaultdict(int)
        for r in week_reports:
            score_str = f' ⭐{r["score"]}' if r['score'] else ''
            lines.append(f'- [{r["area"]}] {r["title"]}{score_str}')
            # 计数方法
            for m in re.split(r'[+、,;/]', r['method']):
                m = m.strip()
                if len(m) > 4: methods_seen[m] += 1
        lines.append('')
        # 高频方法
        if methods_seen:
            lines.append('### 本周高频方法')
            lines.append('')
            top = sorted(methods_seen.items(), key=lambda x: -x[1])[:5]
            for m, n in top:
                lines.append(f'- {m}: {n}次')
            lines.append('')

    # 研究空白提醒
    lines.append('## 🔍 研究空白提醒')
    lines.append('')
    for area in ['公共管理学', '社会学', '老龄化', '青少年研究']:
        n = get_theory_gaps(area)
        if n > 0:
            lines.append(f'- {area}: {n}处研究空白（详见 03_写作素材/研究空白/{area}_研究空白.md）')
    lines.append('')

    # 下周计划
    lines.append('## 📋 下周计划')
    lines.append('')
    gaps_list = [(a, c['pdfs']-c['reports']) for a, c in counts.items()]
    gaps_list.sort(key=lambda x: -x[1])
    for area, gap in gaps_list:
        if gap > 0:
            lines.append(f'- [ ] **{area}**: 补 {gap} 篇精读缺口')
    lines.append('- [ ] 跨篇沉淀重跑（`regenerate_all.py`）')
    lines.append('- [ ] 同步 Obsidian')
    lines.append('')

    content = '\n'.join(lines)
    week_label = f'W{week_start.strftime("%Y-%U")}'
    fp = OUTPUT_DIR / f'周报_{week_label}.md'
    fp.write_text(content, encoding='utf-8')
    print(f'[OK] 周报_{week_label}.md ({len(week_reports)}篇)')

# =========================================================================
# 月报
# =========================================================================
def generate_monthly(target_date=None):
    target = target_date or date.today()
    counts = count_area_reports()
    total_rpt = sum(c['reports'] for c in counts.values())
    total_pdf = sum(c['pdfs'] for c in counts.values())

    lines = [
        f'# {target.year}年{target.month}月 知识库月报',
        f'> 生成: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
        '',
    ]

    # 总览
    lines.append('## 📊 资产总览')
    lines.append('')
    lines.append(f'| 资产类别 | 本月 | 累计 |')
    lines.append(f'|---------|:---:|:----:|')
    lines.append(f'| 精读报告 | — | {total_rpt} |')
    lines.append(f'| PDF原文 | — | {total_pdf} |')

    # 素材库
    for sub in ['摘要', '理论框架', '关键论点', '研究空白']:
        d = MATER_DIR / sub
        n = len(list(d.glob('*.md'))) if d.exists() else 0
        lines.append(f'| 素材-{sub} | — | {n} |')
    lines.append('')

    # 各方向健康度
    lines.append('## 📈 各方向健康度')
    lines.append('')
    lines.append('| 方向 | 精读 | PDF | 覆盖率 | 研究空白 | 评估 |')
    lines.append('|------|:---:|:---:|:-----:|:--------:|:----:|')
    for area in ['公共管理学', '社会学', '老龄化', '青少年研究', '交叉研究']:
        c = counts.get(area, {'reports':0, 'pdfs':0})
        rate = f'{c["reports"]/c["pdfs"]*100:.0f}%' if c['pdfs'] > 0 else '—'
        gaps_n = get_theory_gaps(area)
        # 评估
        if c['reports'] >= 30: assess = '🟢 充足'
        elif c['reports'] >= 20: assess = '🟡 过半'
        elif c['reports'] >= 10: assess = '🟠 积累'
        else: assess = '🔴 薄弱'
        lines.append(f'| {area} | {c["reports"]} | {c["pdfs"]} | {rate} | {gaps_n}处 | {assess} |')
    lines.append('')

    # 知识资产评估
    lines.append('## 🏛️ 知识资产评估')
    lines.append('')
    lines.append('**沉淀产物**:')
    lines.append('')
    # 理论交叉索引
    xref = MATER_DIR / '理论框架/00_理论交叉索引.md'
    if xref.exists():
        with open(xref, 'r', encoding='utf-8') as fh:
            xc = fh.read()
        theory_n = len(re.findall(r'^## ', xc, re.MULTILINE))
        lines.append(f'- 理论交叉索引: {theory_n}个跨篇理论概念')
    # 方法笔记
    method_n = len(list(DIRS['04_methods'].glob('*.md')))
    lines.append(f'- 方法笔记: {method_n}篇')
    lines.append('')

    # 下月建议
    lines.append('## 📋 下月建议')
    lines.append('')
    gaps_list = [(a, c['pdfs']-c['reports']) for a, c in counts.items()]
    gaps_list.sort(key=lambda x: -x[1])
    for area, gap in gaps_list:
        if gap > 0:
            lines.append(f'- [ ] **{area}**: 补齐 {gap} 篇精读缺口')
        else:
            lines.append(f'- [ ] **{area}**: 已达全覆盖，进入深挖阶段')
    lines.append('- [ ] 更新全部索引和跨篇沉淀')
    lines.append('- [ ] 检查研究空白，形成选题方向')
    lines.append('')

    content = '\n'.join(lines)
    fp = OUTPUT_DIR / f'月报_{target.year}-{target.month:02d}.md'
    fp.write_text(content, encoding='utf-8')
    print(f'[OK] 月报_{target.year}-{target.month:02d}.md')

# =========================================================================
# CLI
# =========================================================================
def main():
    import argparse
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    for c in ['daily','weekly','monthly']:
        p = sub.add_parser(c)
        p.add_argument('--date', type=str)
    args = parser.parse_args()

    target = datetime.strptime(args.date, '%Y-%m-%d').date() if getattr(args, 'date', None) else date.today()

    if args.cmd == 'daily': generate_daily(target)
    elif args.cmd == 'weekly': generate_weekly(target)
    elif args.cmd == 'monthly': generate_monthly(target)
    else: parser.print_help()

if __name__ == '__main__':
    main()
