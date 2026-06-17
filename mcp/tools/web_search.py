"""Web Search & Fetch — Claude Code-quality multi-engine search.

Search engines (tried in order):
  1. SearXNG (public instances) — 100+ engines aggregated, free, no key
  2. Brave Search API — Claude Code's own engine, needs BRAVE_API_KEY
  3. Bing Search API — Azure, needs BING_API_KEY
  4. Baidu HTML — always available in China
  5. Bing HTML — works in China
  6. DuckDuckGo HTML/Lite — global fallback

WebFetch: fetches any URL and converts HTML to readable markdown.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
import urllib.parse
import urllib.error
import ssl
from typing import Any

# SearXNG public instances (free, no API key, 100+ engines)
# Only try 2 to keep search fast — if blocked, fall through to Baidu
_SEARXNG_INSTANCES = [
    "https://searx.be",
    "https://search.bus-hit.me",
]


def web_search(
    query: str,
    max_results: int = 10,
    allowed_domains: list[str] | None = None,
    blocked_domains: list[str] | None = None,
    source: str = "auto",
) -> dict[str, Any]:
    """Claude Code-quality web search with multi-engine fallback.

    Priority (China-optimized): Baidu → Brave API → Bing API → SearXNG → DDG

    Returns:
        dict with 'results' (list of {title, url, snippet}), 'source', 'query'
    """
    max_results = min(max_results, 20)
    error_msgs = []

    # Engine 1: Bing HTML (clean HTML, always works in China)
    if source in ("auto", "bing_html"):
        try:
            results = _bing_html_search(query, max_results)
            if results:
                return _build_response(query, results, "bing_html", max_results,
                                       allowed_domains, blocked_domains)
        except Exception as e:
            error_msgs.append(f"bing_html: {e}")

    # Engine 2: Brave Search API (Claude Code's own engine)
    brave_key = os.environ.get("BRAVE_API_KEY", "")
    if source in ("auto", "brave") and brave_key:
        try:
            results = _brave_search(query, max_results, brave_key)
            if results:
                return _build_response(query, results, "brave", max_results,
                                       allowed_domains, blocked_domains)
        except Exception as e:
            error_msgs.append(f"brave: {e}")

    # Engine 3: Bing Search API (Azure)
    bing_key = os.environ.get("BING_API_KEY", "")
    if source in ("auto", "bing") and bing_key:
        try:
            results = _bing_search(query, max_results, bing_key)
            if results:
                return _build_response(query, results, "bing", max_results,
                                       allowed_domains, blocked_domains)
        except Exception as e:
            error_msgs.append(f"bing: {e}")

    # Engine 4: SearXNG (explicit only — too slow when GFW-blocked)
    if source in ("searxng"):
        for instance in _SEARXNG_INSTANCES:
            try:
                results = _searxng_search(query, max_results, instance)
                if results:
                    return _build_response(query, results, f"searxng ({instance})",
                                          max_results, allowed_domains, blocked_domains)
            except Exception as e:
                error_msgs.append(f"searxng({instance}): {e}")

    # Engine 5: Baidu HTML (China fallback)
    if source in ("auto", "baidu"):
        try:
            results = _baidu_search(query, max_results)
            if results:
                return _build_response(query, results, "baidu", max_results,
                                       allowed_domains, blocked_domains)
        except Exception as e:
            error_msgs.append(f"baidu: {e}")

    # Engine 6: DDG HTML (global fallback)
    if source in ("auto", "ddg", "duckduckgo"):
        try:
            results = _ddg_html_search(query, max_results)
            if results:
                return _build_response(query, results, "duckduckgo_html", max_results,
                                       allowed_domains, blocked_domains)
        except Exception as e:
            error_msgs.append(f"ddg_html: {e}")

    # Engine 7: DDG Lite (last resort)
    try:
        results = _ddg_lite_search(query, max_results)
        if results:
            return _build_response(query, results, "duckduckgo_lite", max_results,
                                   allowed_domains, blocked_domains)
    except Exception as e:
        error_msgs.append(f"ddg_lite: {e}")

    return {
        "query": query,
        "results": [],
        "total_results": 0,
        "source": "none",
        "status": "error",
        "errors": error_msgs,
        "suggestion": "Set BRAVE_API_KEY (free: https://brave.com/search/api/) or BING_API_KEY for best results. Errors: " + "; ".join(error_msgs),
    }


def _searxng_search(query: str, max_results: int, instance: str) -> list[dict]:
    """Search via a SearXNG instance (JSON API, 100+ engines aggregated)."""
    encoded = urllib.parse.quote(query)
    # SearXNG JSON API
    url = f"{instance}/search?q={encoded}&format=json&categories=general&language=zh-CN&safesearch=0"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    })
    ctx = ssl.create_default_context()
    resp = urllib.request.urlopen(req, timeout=5, context=ctx)
    data = json.loads(resp.read().decode("utf-8"))

    results = []
    for item in data.get("results", [])[:max_results]:
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": (item.get("content", "") or item.get("snippet", ""))[:300],
        })
    # Also include news if available
    for item in data.get("news", [])[:3]:
        results.append({
            "title": "[News] " + item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": (item.get("content", "") or "")[:300],
        })
    return results


# ═══════════════════════════════════════════════════════════════
# Universal Quality Filter — one chokepoint, all engines
# ═══════════════════════════════════════════════════════════════

# Patterns that identify garbage/parked/aggregator domains
_GARBAGE_URL_PATTERNS = [
    # Parked domains / link farms
    "hao123", "2345.com", "tao123", "9991.com", "duba.com",
    "114la.com", "baiyun.com", "ditie.com",
    # Search engine internal pages (not real results)
    "baidu.com/s?", "baidu.com/link", "baidu.com/search",
    "so.com/s?", "so.com/link", "sogou.com/sogou",
    "/search?q=", "/search/?q=",
    # Ad / tracking redirectors
    "pos.baidu.com", "cpro.baidu.com", "eiv.baidu.com",
    "click.baidu.com",
]

# Title patterns that are definitely garbage
_GARBAGE_TITLE_PATTERNS = [
    # Bare domain names (no real title)
    r"^[a-zA-Z0-9.-]+\.(?:com|cn|net|org|io)(?:https?://.*)?$",
    # Chinese dictionary entries (Bing misinterprets single chars)
    r"^[的地得是了在]\s*(?:拼音|部首|笔画|解释|意思)",
    r"^\S{1,3}\s*[（(].{1,4}[)）]$",  # "近 (汉语汉字)"
    r"^[a-zA-Z]+\.com\s*$",  # "baidu.com"
    r"^\S+\.com\s*https://",  # "domain.comhttps://..."
]

# Reputable domains — boost their quality score
_REPUTABLE_DOMAINS = [
    # News
    "xinhuanet.com", "people.com.cn", "cctv.com", "chinanews.com",
    "thepaper.cn", "guancha.cn", "ifeng.com", "sina.com.cn",
    "sohu.com", "163.com", "qq.com", "toutiao.com",
    "china.com.cn", "gmw.cn", "youth.cn", "ce.cn",
    # Finance
    "eastmoney.com", "sse.com.cn", "szse.cn", "cninfo.com.cn",
    "cs.com.cn", "hexun.com", "jrj.com.cn", "cnstock.com",
    "10jqka.com.cn", "lixinger.com",
    # Government / Education
    "gov.cn", "edu.cn", "ac.cn",
    # Tech / Science
    "36kr.com", "geekpark.net", "jiqizhixin.com",
    "infoq.cn", "csdn.net", "cnblogs.com",
    "zhihu.com", "weixin.qq.com",
    # Global
    "reuters.com", "bbc.com", "bbc.co.uk", "nytimes.com",
    "wsj.com", "bloomberg.com", "ft.com",
    "wikipedia.org", "github.com", "stackoverflow.com",
    "arxiv.org", "medium.com", "reddit.com",
    "theverge.com", "techcrunch.com", "wired.com",
]


def _score_result(r: dict) -> float:
    """Score a search result for quality (higher = better)."""
    score = 0.0
    title = r.get("title", "")
    url = r.get("url", "")
    snippet = r.get("snippet", "")

    # Reputable domain: +3
    for d in _REPUTABLE_DOMAINS:
        if d in url:
            score += 3.0
            break

    # Rich snippet: +2
    if len(snippet) > 80:
        score += 2.0
    elif len(snippet) > 20:
        score += 1.0

    # Good title length: +1
    if 10 <= len(title) <= 150:
        score += 1.0

    # Title looks like Chinese news/article: +1
    if any('一' <= c <= '鿿' for c in title) and len(title) >= 8:
        score += 1.0

    # Penalties
    # Bare domain as title: -5
    import re
    for pat in _GARBAGE_TITLE_PATTERNS:
        if re.search(pat, title):
            score -= 5.0
            break

    # URL is garbage: -10
    for pat in _GARBAGE_URL_PATTERNS:
        if pat in url:
            score -= 10.0
            break

    # Empty snippet penalty: -1
    if not snippet:
        score -= 1.0

    return score


def _build_response(query, results, source, max_results, allowed_domains, blocked_domains):
    """Universal quality filter — one chokepoint for ALL search engines.

    Every result passes through here. Garbage is removed. Quality is scored.
    No engine-specific patches needed.
    """
    import re

    # Merge user blocklist
    all_blocked = list(blocked_domains) if blocked_domains else []

    scored = []
    for r in results:
        url = r.get("url", "")
        title = r.get("title", "")

        # ── Hard filters (definitely garbage) ──
        # Check URL patterns
        if any(g in url for g in _GARBAGE_URL_PATTERNS):
            continue
        # Check user blocklist
        if any(d in url for d in all_blocked):
            continue
        # Check user allowlist
        if allowed_domains and not any(d in url for d in allowed_domains):
            continue
        # Title is mojibake (mostly non-printable)
        printable = sum(1 for c in title if c.isprintable() or '一' <= c <= '鿿')
        if len(title) > 0 and printable / len(title) < 0.5:
            continue
        # URL is just a search engine redirect
        if re.match(r'^https?://[^/]*\.?(?:baidu|so|sogou|bing)\.\w+/.*\?.*[qwd]=', url):
            continue

        # ── Quality scoring ──
        s = _score_result(r)
        if s >= -3.0:  # Only include if not terrible
            scored.append((s, r))

    # Sort by quality (highest first), then take top results
    scored.sort(key=lambda x: -x[0])

    return {
        "query": query,
        "results": [r for _, r in scored[:max_results]],
        "total_results": len(scored),
        "source": source,
        "status": "ok",
    }


# ═══════════════════════════════════════════════════════════════
# Bing HTML Search (accessible globally, no API key needed)
# ═══════════════════════════════════════════════════════════════

def _bing_html_search(query: str, max_results: int = 10) -> list[dict]:
    """Bing HTML search — scrapes cn.bing.com (accessible from China).

    Bing's HTML is cleaner than Baidu's and produces reliable results
    without requiring an API key.
    """
    url = "https://cn.bing.com/search"
    params = urllib.parse.urlencode({
        "q": query,
        "count": str(min(max_results, 20)),
        "setlang": "zh-cn",
    })

    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        f"{url}?{params}",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )

    with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    results = []

    # Bing results are in <li class="b_algo"> blocks
    result_blocks = re.split(
        r'<li[^>]*class="[^"]*b_algo[^"]*"[^>]*>',
        html, re.IGNORECASE,
    )

    for block in result_blocks[1:]:
        if len(results) >= max_results:
            break

        # Title + link: <h2><a href="URL">Title</a></h2>
        link_match = re.search(
            r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
            block, re.IGNORECASE | re.DOTALL,
        )
        if not link_match:
            continue

        href = link_match.group(1)
        title = re.sub(r'<[^>]+>', '', link_match.group(2)).strip()
        # Only strip URLs from title, keep the rest
        title = re.sub(r'https?://\S+', '', title).strip()
        title = html_decode(title)[:200]

        # Snippet: <p> or <div class="b_caption">
        snippet_match = re.search(
            r'<(?:p|div)[^>]*class="[^"]*(?:b_caption|b_lineclamp)[^"]*"[^>]*>(.*?)</(?:p|div)>',
            block, re.IGNORECASE | re.DOTALL,
        )
        snippet = ""
        if snippet_match:
            snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()
        else:
            # Generic text extraction
            text = re.sub(r'<[^>]+>', ' ', block)
            snippet = re.sub(r'\s+', ' ', text).strip()[:300]

        if title and href and 'bing.com' not in href:
            results.append({
                "title": title[:200],
                "url": href,
                "snippet": html_decode(snippet)[:300],
            })

    return results


# ═══════════════════════════════════════════════════════════════
# Baidu Search (China-specific engine)
# ═══════════════════════════════════════════════════════════════

def _baidu_search(query: str, max_results: int = 10) -> list[dict]:
    """Real Baidu search with robust multi-pattern HTML parsing.

    Uses 3 fallback strategies to handle Baidu's frequently changing HTML.
    """
    url = "https://www.baidu.com/s"
    params = urllib.parse.urlencode({
        "wd": query,
        "rn": str(min(max_results, 20)),
        "ie": "utf-8",
    })

    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        f"{url}?{params}",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://www.baidu.com/",
        },
    )

    with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    results = []
    seen_urls = set()

    def _add(title: str, href: str, snippet: str = ""):
        if href in seen_urls:
            return
        seen_urls.add(href)
        if title and len(title) > 2:
            results.append({"title": title.strip()[:200], "url": href, "snippet": snippet.strip()[:300]})

    # Strategy 1: Match h3 titles with t-class + data-showurl/c-abstract snippets
    h3_blocks = re.finditer(
        r'<h3[^>]*class="[^"]*t[^"]*"[^>]*>(.*?)</h3>',
        html, re.IGNORECASE | re.DOTALL,
    )
    for h3 in h3_blocks:
        if len(results) >= max_results:
            break
        block = h3.group(1)
        # Extract link
        link_m = re.search(r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', block, re.IGNORECASE | re.DOTALL)
        if link_m:
            href = link_m.group(1)
            if 'baidu.com' in href or 'javascript:' in href or 'hao123' in href:
                continue
            title = re.sub(r'<[^>]+>', '', link_m.group(2))
            # Try to find snippet near this h3
            snippet = ""
            # Look for c-abstract within 1000 chars after h3
            after_pos = h3.end()
            nearby = html[after_pos:after_pos + 2000]
            snip_m = re.search(r'<(?:span|div)[^>]*class="[^"]*c-abstract[^"]*"[^>]*>(.*?)</(?:span|div)>',
                              nearby, re.IGNORECASE | re.DOTALL)
            if snip_m:
                snippet = re.sub(r'<[^>]+>', '', snip_m.group(1))
            elif not snip_m:
                # Try content-right
                snip_m = re.search(r'<(?:span|div)[^>]*class="[^"]*content-right[^"]*"[^>]*>(.*?)</(?:span|div)>',
                                  nearby, re.IGNORECASE | re.DOTALL)
                if snip_m:
                    snippet = re.sub(r'<[^>]+>', '', snip_m.group(1))
            _add(title, href, snippet)

    # Strategy 2: generic result blocks with c-container
    if not results:
        blocks = re.findall(
            r'<div[^>]*class="[^"]*(?:result|c-container)[^"]*"[^>]*>(.*?)</div>\s*(?=<div[^>]*class="[^"]*(?:result|c-container)|$)',
            html, re.IGNORECASE | re.DOTALL,
        )
        for block in blocks:
            if len(results) >= max_results:
                break
            external_links = re.findall(
                r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
                block, re.IGNORECASE | re.DOTALL,
            )
            for href, title_html in external_links:
                if 'baidu.com' in href or 'javascript:' in href or 'hao123' in href:
                    continue
                title = re.sub(r'<[^>]+>', '', title_html)
                if len(title) > 2:
                    # Extract snippet from span with class
                    snip_m = re.search(r'<(?:span|div)[^>]*class="[^"]*(?:abstract|content|desc)[^"]*"[^>]*>(.*?)</(?:span|div)>',
                                      block, re.IGNORECASE | re.DOTALL)
                    snippet = re.sub(r'<[^>]+>', '', snip_m.group(1)) if snip_m else ""
                    _add(title, href, snippet)
                    break

    # Strategy 3: generic link extraction with smart filtering
    if not results:
        all_links = re.findall(
            r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
            html, re.IGNORECASE | re.DOTALL,
        )
        for href, title_html in all_links:
            if len(results) >= max_results:
                break
            if 'baidu.com' in href or 'javascript:' in href or 'hao123' in href:
                continue
            title = re.sub(r'<[^>]+>', '', title_html)
            if len(title) > 3 and not title.startswith('http'):
                _add(title, href)

    return results


# ═══════════════════════════════════════════════════════════════
# DuckDuckGo HTML Search (global free engine)
# ═══════════════════════════════════════════════════════════════

def _ddg_html_search(query: str, max_results: int = 10) -> list[dict]:
    """Real DuckDuckGo HTML search — POSTs to html.duckduckgo.com.

    This is the non-JS version that DuckDuckGo serves to browsers
    without JavaScript. Returns clean HTML with real search results.
    Works reliably from China (unlike the API).
    """
    # Use html.duckduckgo.com which is the non-JS version
    url = "https://html.duckduckgo.com/html/"
    post_data = urllib.parse.urlencode({"q": query, "b": ""}).encode("utf-8")

    # Bypass SSL verification issues that sometimes occur in China
    ctx = ssl.create_default_context()

    req = urllib.request.Request(
        url,
        data=post_data,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://html.duckduckgo.com",
            "Referer": "https://html.duckduckgo.com/",
        },
    )

    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    return _parse_ddg_html(html, max_results)


def _parse_ddg_html(html: str, max_results: int) -> list[dict]:
    """Parse DuckDuckGo HTML search results page."""
    results = []

    # DDG HTML results are in <div class="result"> blocks
    # Each result has:
    #   <a class="result__a" href="URL">Title</a>
    #   <a class="result__snippet">Snippet text</a>
    #   <span class="result__url">Display URL</span>

    # Split by result blocks
    result_blocks = re.split(
        r'<div[^>]*class="[^"]*result[^"]*"[^>]*>',
        html,
        flags=re.IGNORECASE,
    )

    for block in result_blocks[1:]:  # Skip content before first result
        if len(results) >= max_results:
            break

        # Extract link
        link_match = re.search(
            r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            block, re.IGNORECASE | re.DOTALL,
        )
        if not link_match:
            # Fallback: any link
            link_match = re.search(
                r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
                block, re.IGNORECASE | re.DOTALL,
            )

        if not link_match:
            continue

        href = link_match.group(1)
        # Clean DDG redirect URLs
        if "//duckduckgo.com/l/?" in href:
            parsed = urllib.parse.urlparse(href)
            qs = urllib.parse.parse_qs(parsed.query)
            uddg = qs.get("uddg", [href])[0]
            href = urllib.parse.unquote(uddg)

        title = re.sub(r'<[^>]+>', '', link_match.group(2)).strip()

        # Extract snippet
        snippet_match = re.search(
            r'<[^>]*class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</(?:a|td|div|span)>',
            block, re.IGNORECASE | re.DOTALL,
        )
        snippet = ""
        if snippet_match:
            snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()
        else:
            # Fallback: get any text from the block
            text = re.sub(r'<[^>]+>', ' ', block)
            text = re.sub(r'\s+', ' ', text).strip()
            snippet = text[:300]

        if title and href:
            results.append({
                "title": html_decode(title)[:200],
                "url": href,
                "snippet": html_decode(snippet)[:300],
            })

    return results


# ═══════════════════════════════════════════════════════════════
# DDG Lite (fallback)
# ═══════════════════════════════════════════════════════════════

def _ddg_lite_search(query: str, max_results: int = 10) -> list[dict]:
    """DDG Lite search — ultra-minimal HTML, most reliable fallback."""
    url = "https://lite.duckduckgo.com/lite/"
    post_data = urllib.parse.urlencode({"q": query}).encode()

    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=post_data, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
    })

    with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    results = []
    # DDG Lite: each result row is a <tr> with <a class="result-link">
    link_pattern = re.compile(
        r'<a[^>]*class="result-link"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    snippet_pattern = re.compile(
        r'<td[^>]*class="result-snippet"[^>]*>(.*?)</td>',
        re.IGNORECASE | re.DOTALL,
    )
    links = link_pattern.findall(html)
    snippets = snippet_pattern.findall(html)

    for i, (href, title) in enumerate(links[:max_results]):
        title_clean = html_decode(re.sub(r'<[^>]+>', '', title).strip())
        snippet = ""
        if i < len(snippets):
            snippet = html_decode(re.sub(r'<[^>]+>', '', snippets[i]).strip())
        if title_clean and href:
            results.append({
                "title": title_clean[:200],
                "url": href,
                "snippet": snippet[:300],
            })

    return results


# ═══════════════════════════════════════════════════════════════
# Bing Search API
# ═══════════════════════════════════════════════════════════════

def _bing_search(query: str, max_results: int, api_key: str) -> list[dict]:
    """Bing Web Search API v7 — requires BING_API_KEY."""
    url = "https://api.bing.microsoft.com/v7.0/search"
    params = urllib.parse.urlencode({
        "q": query,
        "count": min(max_results, 20),
        "mkt": "zh-CN",
        "textFormat": "Raw",
    })

    req = urllib.request.Request(
        f"{url}?{params}",
        headers={
            "Ocp-Apim-Subscription-Key": api_key,
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    results = []
    for item in data.get("webPages", {}).get("value", [])[:max_results]:
        results.append({
            "title": item.get("name", "")[:200],
            "url": item.get("url", ""),
            "snippet": item.get("snippet", "")[:300],
        })
    return results


# ═══════════════════════════════════════════════════════════════
# Brave Search API
# ═══════════════════════════════════════════════════════════════

def _brave_search(query: str, max_results: int, api_key: str) -> list[dict]:
    """Brave Search API — requires BRAVE_API_KEY."""
    url = "https://api.search.brave.com/res/v1/web/search"
    params = urllib.parse.urlencode({
        "q": query,
        "count": min(max_results, 20),
    })

    req = urllib.request.Request(
        f"{url}?{params}",
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key,
        },
    )

    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    results = []
    for item in data.get("web", {}).get("results", [])[:max_results]:
        results.append({
            "title": item.get("title", "")[:200],
            "url": item.get("url", ""),
            "snippet": item.get("description", "")[:300],
        })
    return results


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def html_decode(text: str) -> str:
    """Decode HTML entities."""
    import html as _html
    return _html.unescape(text)


# ═══════════════════════════════════════════════════════════════
# WebFetch
# ═══════════════════════════════════════════════════════════════

def web_fetch(url: str, max_length: int = 5000) -> dict[str, Any]:
    """Fetch a URL and convert to readable text.

    Claude Code equivalent: WebFetch tool.
    HTTP upgraded to HTTPS, redirects followed automatically.
    """
    if url.startswith("http://"):
        url = url.replace("http://", "https://", 1)

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,text/plain",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
        }
        # Auto-detect API endpoints
        if "api.github.com" in url:
            headers["Accept"] = "application/vnd.github+json"
            headers["X-GitHub-Api-Version"] = "2022-11-28"
        elif url.endswith(".json") or "api." in url:
            headers["Accept"] = "application/json, text/plain, */*"

        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            final_url = resp.geturl()
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read()

            for enc in ["utf-8", "latin-1", "cp1252", "gbk"]:
                try:
                    html = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                html = raw.decode("utf-8", errors="replace")

        text = _html_to_text(html)
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else final_url

        if len(text) > max_length:
            text = text[:max_length] + f"\n\n[... {len(text) - max_length} more characters]"

        return {
            "url": final_url,
            "original_url": url,
            "title": title[:200],
            "content": text[:max_length],
            "content_length": len(text),
            "content_type": content_type,
            "status": "ok",
        }

    except urllib.error.HTTPError as e:
        return {"url": url, "status": "error",
                "error": f"HTTP {e.code}: {e.reason}",
                "suggestion": f"Server returned {e.code}. Try a different URL."}
    except urllib.error.URLError as e:
        return {"url": url, "status": "error",
                "error": f"Connection failed: {str(e.reason)[:100]}",
                "suggestion": "Check the URL or try again later."}
    except Exception as e:
        return {"url": url, "status": "error", "error": str(e)[:200]}


def _html_to_text(html: str) -> str:
    """Convert HTML to readable plain text."""
    for tag in ['script', 'style', 'nav', 'footer', 'header']:
        html = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', html, flags=re.DOTALL | re.IGNORECASE)
    for tag in ['p', 'div', 'article', 'section', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'tr', 'br']:
        html = re.sub(f'<{tag}[^>]*>', '\n', html, flags=re.IGNORECASE)
        html = re.sub(f'</{tag}>', '\n', html, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', html)
    import html as _html
    text = _html.unescape(text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return '\n'.join(l.strip() for l in text.split('\n') if l.strip())


# ═══════════════════════════════════════════════════════════════
# Registration
# ═══════════════════════════════════════════════════════════════

def register_web_tools(tools_registry: Any) -> None:
    tools_registry.register(
        name="web_search",
        description=(
            "REAL web search using DuckDuckGo HTML (free, no key needed). "
            "Also supports Bing API (set BING_API_KEY) and Brave API (set BRAVE_API_KEY). "
            "Returns titles, URLs, and snippets. Use for current events, docs, and any "
            "question needing up-to-date web information."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "default": 10,
                               "description": "Max results (default 10, max 20)"},
                "allowed_domains": {"type": "array", "items": {"type": "string"},
                                   "description": "Only include these domains"},
                "blocked_domains": {"type": "array", "items": {"type": "string"},
                                   "description": "Exclude these domains"},
                "source": {"type": "string", "default": "auto",
                          "enum": ["auto", "ddg", "bing", "brave"],
                          "description": "Search engine (auto tries all)"},
            },
            "required": ["query"],
        },
        handler=web_search,
        category="web",
    )

    tools_registry.register(
        name="web_fetch",
        description="Fetch a URL and return its content as readable text. Use for reading documentation, articles, and API references.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch"},
                "max_length": {"type": "integer", "default": 5000,
                              "description": "Maximum characters to return"},
            },
            "required": ["url"],
        },
        handler=web_fetch,
        category="web",
    )
