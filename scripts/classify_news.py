"""
V2 新增：AI 分类 + 重要性评级
调用 DeepSeek API 对每条新闻分类(6大类) + 评级(1-5星)
"""
import json
import logging
import re
import time
from datetime import datetime, timezone, timedelta

import requests

from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, NEWS_CATEGORIES, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)
CST = timezone(timedelta(hours=8))


def classify_all_news(news_items: list) -> list:
    """对新闻列表进行分类 + 评级"""
    if not DEEPSEEK_API_KEY:
        logger.warning("DEEPSEEK_API_KEY 未配置，使用关键词规则分类")
        return _classify_by_rules(news_items)

    # 分批处理（每批 10 条，控制 token）
    batch_size = 10
    result = []
    for i in range(0, len(news_items), batch_size):
        batch = news_items[i:i+batch_size]
        classified = _classify_batch_via_deepseek(batch)
        if classified:
            result.extend(classified)
        else:
            # DeepSeek 失败，用规则兜底
            result.extend(_classify_by_rules(batch))
        if i + batch_size < len(news_items):
            time.sleep(1)

    logger.info(f"分类完成：{len(result)} 条新闻")
    return result


def _classify_batch_via_deepseek(batch: list) -> list | None:
    """调用 DeepSeek API 批量分类"""
    news_text = "\n".join([
        f"{i+1}. 标题：{item['title']}\n   摘要：{item.get('summary', '')[:150]}"
        for i, item in enumerate(batch)
    ])

    categories_desc = "\n".join([
        f"- {k}（{v['name']}）"
        for k, v in NEWS_CATEGORIES.items()
    ])

    prompt = f"""你是一个 AI 行业新闻分类器。请对以下 {len(batch)} 条新闻逐一分类并评级。

分类选项：
{categories_desc}

评级维度：行业影响力(40%)、受众广度(30%)、信息独家性(20%)、时效紧迫性(10%)
评级标准：5=必读(行业级重大事件) 4=重要(头部公司重大动态) 3=值得看(有影响力) 2=一般(细分动态) 1=可跳过(价值低)

请返回 JSON 数组，每条新闻一个对象：
[
  {{
    "index": 1,
    "category": "foundation-model",
    "confidence": 0.95,
    "importance": 5,
    "importance_reason": "简短原因"
  }}
]

只输出 JSON，不要其他文字。"""

    try:
        resp = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 2000,
            },
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        json_match = re.search(r"\[.*\]", content, re.DOTALL)
        if not json_match:
            logger.error("DeepSeek 分类输出中未找到 JSON")
            return None

        classifications = json.loads(json_match.group())

        # 将分类结果合并到原始新闻
        for item in batch:
            idx = batch.index(item) + 1
            for cls in classifications:
                if cls.get("index") == idx:
                    item["category"] = cls.get("category", "opinion")
                    item["importance"] = cls.get("importance", 3)
                    item["importance_reason"] = cls.get("importance_reason", "")
                    item["confidence"] = cls.get("confidence", 0.5)
                    break
            # 没匹配到的给默认值
            if not item.get("category"):
                item["category"] = "opinion"
                item["importance"] = 3
                item["importance_reason"] = ""
                item["confidence"] = 0.5

        return batch

    except Exception as e:
        logger.error(f"DeepSeek 分类失败: {e}")
        return None


def _classify_by_rules(news_items: list) -> list:
    """基于关键词规则的分类（DeepSeek 不可用时的兜底方案）"""
    category_keywords = {
        "foundation-model": ["GPT", "Claude", "Gemini", "Llama", "DeepSeek", "大模型", "语言模型",
                             "LLM", "通义", "文心", "智谱", "GLM", "开源模型", "基础模型"],
        "business":         ["融资", "投资", "收购", "IPO", "财报", "商业化", "亿美元", "万元",
                             "funding", "raises", "Series", "billion", "million"],
        "tech-breakthrough": ["论文", "算法", "benchmark", "SOTA", "精度", "架构", "训练方法",
                              "paper", "arxiv", "breakthrough", "innovation"],
        "product":          ["发布", "推出", "上线", "API", "功能", "产品", "更新", "升级",
                             "launch", "release", "update", "feature"],
        "policy":           ["监管", "政策", "法规", "合规", "安全", "隐私", "审查", "沙盒",
                             "regulation", "policy", "governance", "compliance"],
        "opinion":          ["观点", "趋势", "争议", "讨论", "预测", "分析", "看法",
                             "opinion", "trend", "debate", "analysis"],
    }

    for item in news_items:
        text = (item.get("title", "") + " " + item.get("summary", "")).lower()
        best_cat = "opinion"
        best_score = 0

        for cat, keywords in category_keywords.items():
            score = sum(1 for kw in keywords if kw.lower() in text)
            if score > best_score:
                best_score = score
                best_cat = cat

        item["category"] = best_cat
        item["importance"] = 3
        item["importance_reason"] = "规则分类"
        item["confidence"] = 0.5

    return news_items
