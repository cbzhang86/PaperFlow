"""Semantic Scholar API 封装 — 搜索 + 引文推荐

API Key 通过环境变量 S2_API_KEY 传入，不硬编码。
获取地址：https://www.semanticscholar.org/product/api
"""
import sys, os, re, json, time
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# 从环境变量读取 API Key（不硬编码）
# 也支持从 .env 文件自动加载
_env_dotenv = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_dotenv.exists():
    with open(_env_dotenv, "r") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line.startswith("S2_API_KEY="):
                os.environ.setdefault("S2_API_KEY", _line.split("=", 1)[1].strip().strip('"').strip("'"))

API_KEY = os.environ.get("S2_API_KEY")
if not API_KEY:
    print("[S2] 警告: S2_API_KEY 未设置。设置方法: export S2_API_KEY=你的key")
    print("[S2] 获取地址: https://www.semanticscholar.org/product/api")

BASE_URL = "https://api.semanticscholar.org/graph/v1"
MAX_RETRIES = 3
RETRY_DELAY = 2


def _headers() -> dict:
    """构造请求头，含 API Key（如有）"""
    h = {
        "User-Agent": "PaperFlow/1.0 (Academic Research Workflow)",
        "Accept": "application/json",
    }
    if API_KEY:
        h["x-api-key"] = API_KEY
    return h


def _request(url: str, params: dict = None) -> dict:
    """带重试和限速的 GET 请求"""
    if params:
        from urllib.parse import urlencode
        qs = urlencode(
            {k: v for k, v in params.items() if v is not None},
            doseq=True, encoding='utf-8'
        )
        url = f"{url}?{qs}"

    # urlopen 在 Windows 下用 locale 编码，中文路径会报 latin-1 错误
    # 解决方法：只传 ASCII URL
    url = url.encode('utf-8').decode('ascii', errors='ignore')

    for attempt in range(MAX_RETRIES):
        try:
            req = Request(url, headers=_headers())
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 429:
                wait = RETRY_DELAY * (2 ** attempt)
                print(f"[S2] 限速，等待 {wait}s...")
                time.sleep(wait)
                continue
            elif e.code == 403:
                print(f"[S2] 403 Forbidden — API Key 可能无效或被限制")
                return {"error": "forbidden"}
            else:
                print(f"[S2] HTTP {e.code}: {e.reason}")
                return {"error": str(e)}
        except URLError as e:
            print(f"[S2] 网络错误: {e.reason}")
            return {"error": str(e)}
        except Exception as e:
            print(f"[S2] 请求异常: {e}")
            return {"error": str(e)}
    return {"error": "max retries"}


def search(keyword: str, limit: int = 10, fields: str = None) -> list:
    """搜索论文

    Args:
        keyword: 搜索关键词
        limit: 返回条数 (1-100)
        fields: 返回字段，逗号分隔
    Returns:
        [{title, paperId, year, authors, citationCount, openAccessPdf, ...}]
    """
    if not API_KEY:
        print("[S2] 跳过搜索：未设置 S2_API_KEY")
        return []

    if not fields:
        fields = "title,year,authors,citationCount,openAccessPdf,url,externalIds"

    data = _request(
        f"{BASE_URL}/paper/search",
        {"query": keyword, "limit": min(limit, 100), "fields": fields}
    )

    papers = data.get("data", []) if "data" in data else []
    print(f"[S2] 搜索 '{keyword}' → {len(papers)} 篇")
    return papers


def recommend(paper_ids: list, limit: int = 20, fields: str = None) -> list:
    """基于已有论文推荐相关文献（S2 recommend API）

    Args:
        paper_ids: S2 paperId 列表（上限 10 个）
        limit: 推荐条数
        fields: 返回字段
    Returns:
        [{title, paperId, year, authors, citationCount, openAccessPdf, ...}]
    """
    if not API_KEY:
        print("[S2] 跳过推荐：未设置 S2_API_KEY")
        return []

    if not paper_ids:
        return []

    if not fields:
        fields = "title,year,authors,citationCount,openAccessPdf,url,externalIds"

    # S2 recommend API: POST /paper/{paper_id}/recommendations
    # 支持批量推荐，取第一个 paper_id
    pid = paper_ids[0]
    data = _request(
        f"{BASE_URL}/paper/{pid}/recommendations",
        {"limit": min(limit, 100), "fields": fields}
    )

    papers = data.get("data", []) if "data" in data else []
    print(f"[S2] 推荐 (基于 {pid}) → {len(papers)} 篇")
    return papers


def batch_lookup(titles: list) -> dict:
    """通过标题批量查询论文的 S2 paperId

    Args:
        titles: 论文标题列表
    Returns:
        {title: {paperId, ...} or None}
    """
    if not API_KEY:
        return {}

    result = {}
    for t in titles:
        papers = search(t, limit=1, fields="paperId,title,year")
        if papers:
            # 简单标题匹配验证
            best = papers[0]
            if best.get("title", "").lower().strip() == t.lower().strip():
                result[t] = best
            else:
                result[t] = None
        else:
            result[t] = None
        time.sleep(1)  # 限速
    return result
