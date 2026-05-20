"""
学习内容生成脚本
方案 A（MVP）：调用 DeepSeek API，从当日新闻提取 AI 概念并生成学习卡片
方案 B（备选）：预置概念库匹配
"""
import json
import logging
import re
from datetime import datetime, timezone, timedelta

import requests

from config import DEEPSEEK_API_KEY, MAX_LEARNING_CONCEPTS, REQUEST_TIMEOUT
from fetch_news import _make_id

logger = logging.getLogger(__name__)
CST = timezone(timedelta(hours=8))

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"


def generate_learning(news_items: list) -> list:
    """从当日新闻生成学习内容"""
    if DEEPSEEK_API_KEY:
        result = _generate_via_deepseek(news_items)
        if result:
            return result
        logger.warning("DeepSeek 生成失败，降级到预置概念库")

    return _generate_from_fallback(news_items)


def _generate_via_deepseek(news_items: list) -> list | None:
    """调用 DeepSeek API 生成学习卡片"""
    # 构建新闻摘要文本（控制 token 用量）
    news_text = "\n".join([
        f"- {item['title']}: {item.get('summary', '')[:100]}"
        for item in news_items[:20]
    ])

    today = datetime.now(CST).strftime("%Y-%m-%d")
    prompt = f"""你是一个 AI 科普编辑。以下是今天（{today}）的 AI 行业新闻：

{news_text}

请从这些新闻中提取 {MAX_LEARNING_CONCEPTS} 个值得学习的 AI 概念/术语，为每个概念生成学习卡片。

要求：
1. 选择最具代表性、适合非技术背景读者学习的概念
2. 每个概念用以下 JSON 格式输出
3. 解释要通俗易懂，避免堆砌术语
4. 举例要贴近实际生活/商业场景

输出格式（严格 JSON 数组）：
[
  {{
    "concept": "概念名称（中文）",
    "concept_en": "英文原名",
    "definition": "一句话定义（30字以内）",
    "explanation": "通俗解释（150-200字）",
    "example": "实际应用场景举例（100字以内）",
    "difficulty": "beginner | intermediate | advanced"
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
                "temperature": 0.7,
                "max_tokens": 3000,
            },
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        # 提取 JSON（防止模型多输出了非 JSON 内容）
        json_match = re.search(r"\[.*\]", content, re.DOTALL)
        if not json_match:
            logger.error("DeepSeek 输出中未找到 JSON")
            return None

        concepts = json.loads(json_match.group())
        today_str = datetime.now(CST).strftime("%Y-%m-%d")

        # 补全字段
        result = []
        for i, c in enumerate(concepts[:MAX_LEARNING_CONCEPTS]):
            result.append({
                "id": f"learn_{today_str.replace('-', '')}_{i+1:03d}",
                "concept": c.get("concept", ""),
                "concept_en": c.get("concept_en", ""),
                "definition": c.get("definition", ""),
                "explanation": c.get("explanation", ""),
                "example": c.get("example", ""),
                "articles": [],   # MVP 暂不自动搜索推荐文章
                "video": None,
                "difficulty": c.get("difficulty", "beginner"),
                "date": today_str,
            })
        logger.info(f"DeepSeek 生成了 {len(result)} 个学习概念")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"DeepSeek 返回 JSON 解析失败: {e}")
    except Exception as e:
        logger.error(f"DeepSeek API 调用失败: {e}")
    return None


# ─── 备选方案：预置概念库 ─────────────────────────────────────────────────────

CONCEPT_LIBRARY = {
    "RAG": {
        "concept_en": "Retrieval-Augmented Generation",
        "definition": "让大模型在回答时能检索外部知识库，解决知识过时和幻觉问题。",
        "explanation": "大模型训练完成后，知识就固定了。RAG 的做法是：用户提问时，先从外部知识库搜出相关内容，再把这些内容连同问题一起喂给模型，模型就能给出基于最新信息的回答。简单说就是「带着参考资料回答问题」。",
        "example": "企业内部客服机器人，从公司文档库检索最新政策后再回答员工问题。",
        "difficulty": "beginner",
        "keywords": ["RAG", "检索", "知识库", "向量"],
    },
    "Agent": {
        "concept_en": "AI Agent",
        "definition": "能自主规划并执行多步骤任务的 AI 系统，可调用工具、做决策。",
        "explanation": "普通 AI 对话是一问一答。Agent 不一样——你给它一个目标，它自己拆解任务、决定用什么工具、一步步执行，直到目标达成。比如「帮我调研竞品并写报告」，Agent 会自己搜索、整理、写作，全程不需要你手动介入。",
        "example": "OpenClaw 收到「帮我查天气」后，自动调用天气 API 获取数据，再整理成自然语言回复。",
        "difficulty": "beginner",
        "keywords": ["Agent", "智能体", "自主", "工具调用"],
    },
    "Fine-tuning": {
        "concept_en": "Fine-tuning",
        "definition": "在预训练大模型基础上，用特定领域数据继续训练，提升垂直场景表现。",
        "explanation": "预训练大模型是全能通才，微调就是让它上「专业培训班」。用特定领域数据继续训练，让它在某个垂直领域更擅长。比如用医疗病历数据微调后，模型就更懂临床思维。微调成本比从头训练低得多，但能显著提升特定场景表现。",
        "example": "催收机构用历史案例数据微调大模型，让它更准确地判断负债人还款概率。",
        "difficulty": "intermediate",
        "keywords": ["微调", "Fine-tuning", "训练", "模型"],
    },
    "大模型": {
        "concept_en": "Large Language Model (LLM)",
        "definition": "参数量达到十亿级别以上、能理解和生成自然语言的 AI 模型。",
        "explanation": "大模型就是用海量文本数据训练出来的超大型 AI，它理解语言、写作、推理、编程样样都会。「大」指的是模型参数数量（GPT-4 约 1.8 万亿参数）。现在说的 AI 对话产品（ChatGPT、DeepSeek、文心一言等）背后都是大模型。",
        "example": "你在微信和 OpenClaw 对话，背后调用的 deepseek-chat 就是一个大模型。",
        "difficulty": "beginner",
        "keywords": ["大模型", "LLM", "GPT", "DeepSeek", "Claude"],
    },
    "多模态": {
        "concept_en": "Multimodal AI",
        "definition": "能同时处理文字、图片、语音、视频等多种信息类型的 AI 模型。",
        "explanation": "早期 AI 只能处理文字。多模态 AI 打通了文字、图片、音频、视频等不同「感官通道」。比如你发一张图片给 AI，它能理解图中内容并回答问题；你描述一段文字，它能生成对应的图片或视频。GPT-4V、Gemini、Sora 都是典型的多模态 AI 产品。",
        "example": "「帮我把这张产品截图翻译成英文」——AI 同时理解图片和文字，直接输出翻译结果。",
        "difficulty": "beginner",
        "keywords": ["多模态", "图片", "视觉", "语音", "multimodal"],
    },
}

KEYWORD_TO_CONCEPT = {}
for concept_name, concept_data in CONCEPT_LIBRARY.items():
    for kw in concept_data.get("keywords", []):
        KEYWORD_TO_CONCEPT[kw.lower()] = concept_name


def _generate_from_fallback(news_items: list) -> list:
    """从预置概念库匹配当日相关概念"""
    news_text = " ".join([item.get("title", "") + " " + item.get("summary", "") for item in news_items])
    news_lower = news_text.lower()

    # 统计每个概念在新闻中出现的频次
    concept_scores: dict[str, int] = {}
    for kw, concept_name in KEYWORD_TO_CONCEPT.items():
        count = news_lower.count(kw)
        if count > 0:
            concept_scores[concept_name] = concept_scores.get(concept_name, 0) + count

    # 取出现频次最高的若干概念
    selected = sorted(concept_scores.items(), key=lambda x: x[1], reverse=True)[:MAX_LEARNING_CONCEPTS]

    # 如果没匹配到任何概念，返回默认的入门概念
    if not selected:
        selected = [("大模型", 1), ("Agent", 1), ("RAG", 1)]

    today_str = datetime.now(CST).strftime("%Y-%m-%d")
    result = []
    for i, (concept_name, _) in enumerate(selected):
        data = CONCEPT_LIBRARY.get(concept_name, {})
        result.append({
            "id": f"learn_{today_str.replace('-', '')}_{i+1:03d}",
            "concept": concept_name,
            "concept_en": data.get("concept_en", ""),
            "definition": data.get("definition", ""),
            "explanation": data.get("explanation", ""),
            "example": data.get("example", ""),
            "articles": [],
            "video": None,
            "difficulty": data.get("difficulty", "beginner"),
            "date": today_str,
        })

    logger.info(f"预置库匹配了 {len(result)} 个学习概念")
    return result
