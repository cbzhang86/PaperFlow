#!/c/Users/Administrator/AppData/Local/Programs/Python/Python311 python
"""统一采集调度 — 自动判断用哪个源，全流程自动化"""
import sys, os, re, time, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from base import KEYWORD_POOL, get_existing_titles, archive_pdf, AREA_CONFIG

SOURCES = []

def load_sources():
    """动态加载所有 *_source.py 模块"""
    src_dir = Path(__file__).parent
    # 支持 _source.py（master）和 .py（framework）两种命名
    for f in sorted(src_dir.glob("*_source.py")) + sorted(src_dir.glob("arxiv.py")) + sorted(src_dir.glob("openalex.py")):
        name = f.stem
        if name in ("base", "multi_source", "search", "fetch", "ncpssd", "cleanup_filenames", "standardize_filenames"):
            continue
        # 跳过 _source.py 对应的同名 .py
        if f.name.endswith("_source.py"):
            base_name = name.replace("_source", "")
            if (src_dir / f"{base_name}.py").exists():
                continue
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(name, str(f))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for attr in dir(mod):
                cls = getattr(mod, attr)
                if isinstance(cls, type) and hasattr(cls, 'name') and hasattr(cls, 'search') and hasattr(cls, 'download'):
                    if cls.__name__ not in ('BaseSource',):
                        instance = cls()
                        SOURCES.append(instance)
                        print(f"  [加载源] {instance.name()}")
        except Exception as e:
            print(f"  [加载失败] {name}: {e}")

def should_use_source(keyword):
    """判断关键词应该用哪些源
    规则：有中文 → 所有源都试（开放源也支持中文搜索）
          纯英文 → arXiv/OpenAlex
    """
    has_chinese = bool(re.search(r'[一-鿿]', keyword))

    if has_chinese:
        return ["ncpssd", "arxiv", "openalex"]  # 中文关键词也用开放源
    else:
        return ["arxiv", "openalex", "semantic_scholar"]  # 纯英文 → 开放源

def search_all(keyword, limit=5, direction=None):
    """在所有合适的源中搜索，返回合并+去重后的结果"""
    if not SOURCES:
        load_sources()

    sources_to_use = should_use_source(keyword)
    existing = get_existing_titles()
    all_results = []
    seen_titles = set()

    for src in SOURCES:
        if src.name() not in sources_to_use:
            continue
        print(f"\n[{src.name()}] 搜索: {keyword}")
        try:
            papers = src.search(keyword, limit)
        except Exception as e:
            print(f"  ⚠️ 搜索失败: {e}")
            continue
        for p in papers:
            t_clean = re.sub(r"\s+", "", p["title"].strip().lower())[:60]
            if t_clean in seen_titles:
                continue
            seen_titles.add(t_clean)
            is_dup = any(t_clean in e for e in existing)
            p["duplicate"] = is_dup
            p["direction"] = direction
            all_results.append(p)
            status = "已有" if is_dup else "新"
            print(f"  [{status}] [{p['source']}] {p['title'][:60]}")
        time.sleep(1)

    return all_results

def download_all(papers, max_download=3):
    """从搜索结果中下载新论文"""
    downloaded = 0
    for p in papers:
        if downloaded >= max_download:
            break
        if p.get("duplicate"):
            continue
        for src in SOURCES:
            if src.name() == p["source"]:
                print(f"\n  下载: {p['title'][:40]}")
                try:
                    if src.download(p):
                        downloaded += 1
                except Exception as e:
                    print(f"  ⚠️ 下载失败: {e}")
                time.sleep(1)
                break
    return downloaded

def cmd_search(keyword, limit=5):
    """搜索（不下载）"""
    results = search_all(keyword, limit)
    print(f"\n总计: {len(results)} 条结果")
    new_count = sum(1 for r in results if not r.get("duplicate"))
    print(f"新论文: {new_count} 篇")

def cmd_search_dl(keyword, limit=3, direction=None):
    """搜索并下载新论文"""
    results = search_all(keyword, limit, direction=direction)
    new_papers = [r for r in results if not r.get("duplicate")]
    if not new_papers:
        print("\n无新论文需要下载")
        return
    n = download_all(new_papers, max_download=limit)
    print(f"\n下载完成: {n} 篇")

def cmd_pool(area, limit=3):
    """按方向从关键词池批量搜索下载（自动判断源）"""
    kws = KEYWORD_POOL.get(area, [])
    if not kws:
        print(f"[ERROR] 未知方向: {area}")
        return
    total_dl = 0
    for kw in kws:
        print(f"\n{'='*50}")
        print(f"关键词: {kw}")
        print(f"{'='*50}")
        cmd_search_dl(kw, limit, direction=area)
        total_dl += 1
    print(f"\n方向 [{area}] 批量下载完成")

def cmd_status():
    """查看所有源状态"""
    if not SOURCES:
        load_sources()
    print(f"已加载源: {len(SOURCES)}")
    for src in SOURCES:
        print(f"  ✅ {src.name()}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="智能多源采集")
    sub = parser.add_subparsers(dest="cmd")

    p_s = sub.add_parser("search", help="搜索（智能判断源）")
    p_s.add_argument("keyword")
    p_s.add_argument("--limit", type=int, default=5)
    p_s.add_argument("--direction", help="研究方向（如 老龄化研究）")

    p_sd = sub.add_parser("search-dl", help="搜索并下载")
    p_sd.add_argument("keyword")
    p_sd.add_argument("--limit", type=int, default=3)
    p_sd.add_argument("--direction", help="研究方向（如 老龄化研究）")

    p_pool = sub.add_parser("pool", help="从关键词池批量搜索下载")
    p_pool.add_argument("area", choices=list(KEYWORD_POOL.keys()))
    p_pool.add_argument("--limit", type=int, default=3)

    p_stat = sub.add_parser("status", help="查看源状态")

    args = parser.parse_args()
    if args.cmd == "search":
        cmd_search(args.keyword, args.limit)
    elif args.cmd == "search-dl":
        cmd_search_dl(args.keyword, args.limit, direction=args.direction)
    elif args.cmd == "pool":
        cmd_pool(args.area, args.limit)
    elif args.cmd == "status":
        cmd_status()
    else:
        parser.print_help()
