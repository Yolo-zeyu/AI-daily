"""
投融资信息采集脚本
数据源：36Kr 融资频道、Crunchbase News RSS
"""
import time
import logging
from datetime import datetime, timezone, timedelta

import requests
import feedparser
from bs4 import BeautifulSoup

from config import (
    DEAL_SOURCES, MAX_DEALS_PER_SOURCE, AI_KEYWORDS,
    REQUEST_DELAY, REQUEST_TIMEOUT, USER_AGENT
)
from fetch_news import _make_id, _parse_time

logger = logging.getLogger(__name__)
CST = timezone(timedelta(hours=8))


def fetch_all_deals() -> list:
    """采集所有来源的投融资信息，过滤 AI 相关后返回"""
    all_deals = []

    sources = sorted(DEAL_SOURCES, key=lambda x: x["priority"])
    for source in sources:
        try:
            logger.info(f"采集投融资: {source['name']}")
            if source["type"] == "rss":
                items = _fetch_deal_rss(source)
            elif source["type"] == "scrape":
                items = _fetch_36kr_deals(source)
            else:
                items = []
            all_deals.extend(items[:MAX_DEALS_PER_SOURCE])
            logger.info(f"  {source['name']}: 获取 {len(items)} 条")
        except Exception as e:
            logger.error(f"采集 {source['name']} 失败: {e}")
        time.sleep(REQUEST_DELAY)

    # 过滤 AI 相关
    ai_deals = [d for d in all_deals if _is_ai_related(d)]
    # 去重（同公司同轮次）
    seen = set()
    deduped = []
    for deal in ai_deals:
        key = f"{deal.get('company', '')}_{deal.get('round', '')}"
        if key not in seen:
            seen.add(key)
            deduped.append(deal)

    # 按金额排序（尽力解析，无法解析的排最后）
    deduped.sort(key=lambda x: _parse_amount(x.get("amount", "")), reverse=True)
    logger.info(f"投融资总计: 共 {len(all_deals)} 条，AI 相关 {len(ai_deals)} 条，去重后 {len(deduped)} 条")
    return deduped


def _fetch_36kr_deals(source: dict) -> list:
    """采集 36Kr 融资频道"""
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "zh-CN,zh;q=0.9"}
    resp = requests.get(source["url"], headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    # 36Kr 融资页文章卡片（selector 随页面结构可能需要维护）
    cards = soup.select("div.articleCard, .flow-list .item, article")
    if not cards:
        cards = soup.find_all("a", href=lambda h: h and "/p/" in str(h))

    for card in cards[:MAX_DEALS_PER_SOURCE]:
        a = card.find("a") if card.name != "a" else card
        if not a:
            continue
        title = a.get_text(strip=True)
        href = a.get("href", "")
        if not href.startswith("http"):
            href = "https://36kr.com" + href
        if not title or len(title) < 5:
            continue

        # 从标题解析融资信息
        deal = _parse_deal_from_title(title, href, source["name"])
        if deal:
            items.append(deal)

    return items


def _fetch_deal_rss(source: dict) -> list:
    """从 RSS 采集投融资"""
    feed = feedparser.parse(source["url"])
    items = []
    for entry in feed.entries[:MAX_DEALS_PER_SOURCE]:
        title = entry.get("title", "")
        href = entry.get("link", source["url"])
        deal = _parse_deal_from_title(title, href, source["name"])
        if deal:
            items.append(deal)
    return items


def _parse_deal_from_title(title: str, url: str, source_name: str) -> dict | None:
    """从标题文本尝试解析融资信息"""
    # 简单关键词判断是否是融资新闻
    deal_keywords = ["融资", "完成", "获得", "轮", "亿", "万美元", "million", "billion", "raises", "funding", "Series"]
    if not any(kw.lower() in title.lower() for kw in deal_keywords):
        return None

    return {
        "id": _make_id("deal", url),
        "company": _extract_company(title),
        "company_en": None,
        "round": _extract_round(title),
        "amount": _extract_amount(title),
        "amount_usd": None,
        "investors": [],
        "industry_tags": _extract_deal_tags(title),
        "source": source_name,
        "source_url": url,
        "publish_time": datetime.now(CST).strftime("%Y-%m-%d"),
        "description": title[:100],
    }


def _is_ai_related(deal: dict) -> bool:
    """判断投融资是否与 AI 相关"""
    text = " ".join([
        deal.get("company", ""),
        deal.get("description", ""),
        " ".join(deal.get("industry_tags", [])),
    ]).lower()
    return any(kw.lower() in text for kw in AI_KEYWORDS)


def _parse_amount(amount_str: str) -> float:
    """尽力把金额字符串转为数字（人民币亿元），用于排序"""
    if not amount_str:
        return -1
    s = amount_str.replace(",", "").replace(" ", "")
    try:
        if "亿美元" in s or "billion" in s.lower():
            import re
            nums = re.findall(r"[\d.]+", s)
            return float(nums[0]) * 7 * 1e8 if nums else -1
        if "亿" in s:
            import re
            nums = re.findall(r"[\d.]+", s)
            return float(nums[0]) * 1e8 if nums else -1
        if "万" in s:
            import re
            nums = re.findall(r"[\d.]+", s)
            return float(nums[0]) * 1e4 if nums else -1
        if "million" in s.lower():
            import re
            nums = re.findall(r"[\d.]+", s)
            return float(nums[0]) * 7 * 1e6 if nums else -1
    except Exception:
        pass
    return 0


def _extract_company(title: str) -> str:
    """从标题提取公司名（简单规则，实际应用可接 NER）"""
    # 常见格式：XX公司完成/获得/宣布...
    import re
    patterns = [
        r"^(.{2,10}?)(?:完成|获得|宣布|获|融)",
        r"^(.{2,15}?)\s+(?:raises|secures|closes)",
    ]
    for p in patterns:
        m = re.search(p, title)
        if m:
            return m.group(1).strip()
    return title[:10]


def _extract_round(title: str) -> str:
    """从标题提取融资轮次"""
    import re
    rounds = ["Pre-A轮", "天使轮", "种子轮", "A+轮", "B+轮", "C+轮", "A轮", "B轮", "C轮", "D轮", "E轮",
              "Series A", "Series B", "Series C", "Series D", "Pre-IPO", "战略融资"]
    for r in rounds:
        if r.lower() in title.lower():
            return r
    return "战略融资"


def _extract_amount(title: str) -> str:
    """从标题提取金额"""
    import re
    patterns = [
        r"(\d+[\d.,]*\s*亿(?:美元|人民币|元)?)",
        r"(\d+[\d.,]*\s*万(?:美元|人民币|元)?)",
        r"(\$[\d.,]+\s*[BMK]?)",
        r"([\d.,]+\s*(?:billion|million)\s*(?:dollars?)?)",
        r"(数[十百千万亿]+(?:元|美元|人民币)?)",
    ]
    for p in patterns:
        m = re.search(p, title, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return "金额未披露"


def _extract_deal_tags(title: str) -> list:
    """从融资标题提取行业标签"""
    tag_map = {
        "大模型": "大模型", "AI": "AI", "人工智能": "AI",
        "芯片": "AI芯片", "GPU": "AI芯片",
        "机器人": "机器人", "自动驾驶": "自动驾驶",
        "医疗": "AI医疗", "教育": "AI教育", "游戏": "AI游戏",
        "安全": "AI安全", "金融": "AI金融",
    }
    found = []
    for kw, tag in tag_map.items():
        if kw.lower() in title.lower() and tag not in found:
            found.append(tag)
        if len(found) >= 3:
            break
    return found
