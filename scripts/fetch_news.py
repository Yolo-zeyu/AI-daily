"""
新闻采集脚本
支持：RSS、API（HN）、网页解析（36Kr、量子位）
"""
import time
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher

import requests
import feedparser
from bs4 import BeautifulSoup

from config import (
    NEWS_SOURCES, MAX_NEWS_PER_SOURCE, REQUEST_DELAY,
    REQUEST_TIMEOUT, USER_AGENT
)

logger = logging.getLogger(__name__)

CST = timezone(timedelta(hours=8))


def fetch_all_news() -> list:
    """采集所有来源的新闻，去重后返回"""
    all_news = []

    # 按优先级排序
    sources = sorted(NEWS_SOURCES, key=lambda x: x["priority"])
    for source in sources:
        try:
            logger.info(f"采集新闻: {source['name']}")
            if source["type"] == "rss":
                items = fetch_rss(source)
            elif source["type"] == "api":
                items = fetch_hn_api(source)
            elif source["type"] == "scrape":
                items = fetch_scrape(source)
            else:
                items = []
            all_news.extend(items[:MAX_NEWS_PER_SOURCE])
            logger.info(f"  {source['name']}: 获取 {len(items)} 条")
        except Exception as e:
            logger.error(f"采集 {source['name']} 失败: {e}")
        time.sleep(REQUEST_DELAY)

    # 去重
    deduped = deduplicate(all_news)
    # 时间倒序
    deduped.sort(key=lambda x: x.get("publish_time", ""), reverse=True)
    logger.info(f"新闻总计: 去重前 {len(all_news)} 条，去重后 {len(deduped)} 条")
    return deduped


def fetch_rss(source: dict) -> list:
    """解析 RSS Feed"""
    feed = feedparser.parse(source["url"])
    items = []
    today = datetime.now(CST).date()

    for entry in feed.entries[:MAX_NEWS_PER_SOURCE]:
        # 过滤非今日内容（宽松：允许近 24 小时）
        pub_time = _parse_time(entry.get("published") or entry.get("updated", ""))

        item = {
            "id": _make_id("news", entry.get("link", entry.get("title", ""))),
            "title": entry.get("title", "").strip(),
            "title_en": entry.get("title", "").strip() if source["language"] == "en" else None,
            "summary": _clean_html(entry.get("summary", "") or entry.get("description", ""))[:300],
            "summary_translated": None,
            "source": source["name"],
            "source_url": entry.get("link", source["url"]),
            "cover_image": _extract_image(entry),
            "publish_time": pub_time,
            "category": "news",
            "language": source["language"],
            "tags": _extract_tags(entry.get("title", "") + " " + entry.get("summary", "")),
        }
        if source["language"] == "zh":
            item["title_en"] = None
        items.append(item)
    return items


def fetch_hn_api(source: dict) -> list:
    """从 HN Algolia API 获取 AI 相关文章"""
    resp = requests.get(source["url"], timeout=REQUEST_TIMEOUT,
                        headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    hits = resp.json().get("hits", [])
    items = []
    for hit in hits[:MAX_NEWS_PER_SOURCE]:
        items.append({
            "id": _make_id("news", hit.get("url", hit.get("objectID", ""))),
            "title": hit.get("title", "").strip(),
            "title_en": hit.get("title", "").strip(),
            "summary": f"HN 讨论：{hit.get('points', 0)} 分，{hit.get('num_comments', 0)} 条评论",
            "summary_translated": None,
            "source": "Hacker News",
            "source_url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            "cover_image": None,
            "publish_time": hit.get("created_at", ""),
            "category": "news",
            "language": "en",
            "tags": ["Hacker News"],
        })
    return items


def fetch_scrape(source: dict) -> list:
    """网页解析（36Kr、量子位等）"""
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "zh-CN,zh;q=0.9"}
    resp = requests.get(source["url"], headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []

    if "36kr.com" in source["url"]:
        items = _scrape_36kr(soup, source)
    elif "qbitai.com" in source["url"]:
        items = _scrape_qbitai(soup, source)
    else:
        # 通用：提取所有 <article> 标签
        for article in soup.find_all("article")[:MAX_NEWS_PER_SOURCE]:
            a = article.find("a")
            if a:
                items.append({
                    "id": _make_id("news", a.get("href", "")),
                    "title": a.get_text(strip=True),
                    "title_en": None,
                    "summary": "",
                    "summary_translated": None,
                    "source": source["name"],
                    "source_url": a.get("href", source["url"]),
                    "cover_image": None,
                    "publish_time": datetime.now(CST).isoformat(),
                    "category": "news",
                    "language": source["language"],
                    "tags": [],
                })
    return items


def _scrape_36kr(soup, source):
    """解析 36Kr 文章列表"""
    items = []
    # 36Kr 文章列表 selector（可能随时变更，需要定期维护）
    cards = soup.select("div.articleCard, .flow-list .item, article")
    if not cards:
        cards = soup.find_all("a", href=lambda h: h and "/p/" in str(h))

    for card in cards[:MAX_NEWS_PER_SOURCE]:
        a = card.find("a") if card.name != "a" else card
        if not a:
            continue
        href = a.get("href", "")
        if not href.startswith("http"):
            href = "https://36kr.com" + href
        title = a.get_text(strip=True)
        if not title or len(title) < 5:
            continue
        items.append({
            "id": _make_id("news", href),
            "title": title,
            "title_en": None,
            "summary": "",
            "summary_translated": None,
            "source": source["name"],
            "source_url": href,
            "cover_image": None,
            "publish_time": datetime.now(CST).isoformat(),
            "category": "news",
            "language": "zh",
            "tags": _extract_tags(title),
        })
    return items


def _scrape_qbitai(soup, source):
    """解析量子位文章列表"""
    items = []
    posts = soup.select("article.post, .post-item, .content-list .item")
    if not posts:
        posts = soup.find_all("h2")

    for post in posts[:MAX_NEWS_PER_SOURCE]:
        a = post.find("a") if post.name != "a" else post
        if not a:
            continue
        href = a.get("href", "")
        if not href.startswith("http"):
            href = "https://www.qbitai.com" + href
        title = a.get_text(strip=True)
        if not title or len(title) < 5:
            continue
        items.append({
            "id": _make_id("news", href),
            "title": title,
            "title_en": None,
            "summary": "",
            "summary_translated": None,
            "source": source["name"],
            "source_url": href,
            "cover_image": None,
            "publish_time": datetime.now(CST).isoformat(),
            "category": "news",
            "language": "zh",
            "tags": _extract_tags(title),
        })
    return items


# ─── 工具函数 ─────────────────────────────────────────────────────────────────

def deduplicate(items: list, threshold: float = 0.8) -> list:
    """按标题相似度去重"""
    seen = []
    result = []
    for item in items:
        title = item.get("title", "")
        is_dup = any(
            SequenceMatcher(None, title, s).ratio() > threshold
            for s in seen
        )
        if not is_dup:
            seen.append(title)
            result.append(item)
    return result


def _make_id(prefix: str, url: str) -> str:
    today = datetime.now(CST).strftime("%Y%m%d")
    short = hashlib.md5(url.encode()).hexdigest()[:6]
    return f"{prefix}_{today}_{short}"


def _parse_time(time_str: str) -> str:
    """尽力解析各种时间格式，返回 ISO 8601"""
    if not time_str:
        return datetime.now(CST).isoformat()
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(time_str).isoformat()
    except Exception:
        pass
    try:
        return datetime.fromisoformat(time_str).isoformat()
    except Exception:
        pass
    return datetime.now(CST).isoformat()


def _clean_html(html: str) -> str:
    """去除 HTML 标签，保留纯文本"""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def _extract_image(entry) -> str | None:
    """从 RSS entry 提取封面图"""
    # 从 media:content 或 enclosure 中提取
    media = entry.get("media_content", [])
    if media:
        return media[0].get("url")
    enclosures = entry.get("enclosures", [])
    if enclosures:
        return enclosures[0].get("href")
    # 从内容中找 img 标签
    content = entry.get("content", [{}])[0].get("value", "")
    if content:
        soup = BeautifulSoup(content, "html.parser")
        img = soup.find("img")
        if img:
            return img.get("src")
    return None


def _extract_tags(text: str) -> list:
    """从文本中提取 AI 相关标签"""
    from config import AI_KEYWORDS
    found = []
    tag_map = {
        "大模型": "大模型", "LLM": "大模型", "GPT": "大模型", "Claude": "大模型",
        "融资": "融资", "投资": "融资",
        "开源": "开源",
        "自动驾驶": "自动驾驶",
        "芯片": "AI芯片", "GPU": "AI芯片",
        "机器人": "机器人",
        "Agent": "智能体", "智能体": "智能体",
        "多模态": "多模态",
        "产品": "产品发布", "发布": "产品发布",
    }
    for kw, tag in tag_map.items():
        if kw.lower() in text.lower() and tag not in found:
            found.append(tag)
        if len(found) >= 3:
            break
    return found
