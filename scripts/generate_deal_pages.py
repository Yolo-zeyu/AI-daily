"""
V2 新增：融资详情页生成
为每条融资信息生成独立 HTML 文件 + 用 DeepSeek 生成公司简介和融资历史
"""
import json
import logging
import re
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)
CST = timezone(timedelta(hours=8))


def generate_deal_pages(deals: list, news_items: list, base_dir: str) -> list:
    """
    为每条融资信息生成详情页 HTML
    同时补充 company_intro、related_articles、funding_history
    """
    date_str = datetime.now(CST).strftime("%Y-%m-%d")
    deals_dir = Path(base_dir) / "data" / "deals" / date_str
    deals_dir.mkdir(parents=True, exist_ok=True)

    # 用 DeepSeek 批量补充详情
    if DEEPSEEK_API_KEY:
        deals = _enrich_deals_via_deepseek(deals, news_items)

    for deal in deals:
        slug = _slugify(deal.get("company", "unknown"))
        html_path = deals_dir / f"{slug}.html"
        html_content = _build_deal_html(deal, date_str)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        # 记录详情页路径
        deal["detail_url"] = f"data/deals/{date_str}/{slug}.html"

    logger.info(f"生成了 {len(deals)} 个融资详情页")
    return deals


def _enrich_deals_via_deepseek(deals: list, news_items: list) -> list:
    """调用 DeepSeek 补充公司简介和融资历史"""
    for deal in deals[:5]:  # 限制最多5条，控制成本
        company = deal.get("company", "")
        if not company:
            continue

        # 查找相关报道
        related = []
        for news in news_items:
            if company.lower() in news.get("title", "").lower() or \
               company.lower() in news.get("summary", "").lower():
                related.append({
                    "title": news.get("title", ""),
                    "url": news.get("source_url", ""),
                    "source": news.get("source", ""),
                })
        deal["related_articles"] = related[:5]

        # 用 DeepSeek 生成公司简介 + 融资历史
        prompt = f"""请提供关于 {company} 这家公司的信息，返回严格 JSON：
{{
  "company_intro": "50-100字公司简介，包括主营业务、核心产品和行业地位",
  "funding_history": [
    {{"round": "轮次", "date": "YYYY.MM", "amount": "金额", "investors": ["投资方"]}}
  ]
}}

只输出 JSON，不要其他文字。如果不确定具体信息，请合理推测并标注。"""

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
                    "temperature": 0.5,
                    "max_tokens": 1000,
                },
                timeout=60,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]

            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                deal["company_intro"] = data.get("company_intro", "")
                deal["funding_history"] = data.get("funding_history", [])
        except Exception as e:
            logger.error(f"DeepSeek 生成公司详情失败 ({company}): {e}")

    return deals


def _slugify(text: str) -> str:
    """将公司名转为 URL-safe slug"""
    slug = re.sub(r"[^\w\u4e00-\u9fff-]", "", text.lower())
    slug = slug.replace(" ", "-")
    if not slug:
        slug = "company"
    return slug[:50]


def _build_deal_html(deal: dict, date_str: str) -> str:
    """生成融资详情页 HTML（避免 f-string 嵌套，用 .format() + 提前构建）"""
    company = deal.get("company", "")
    company_en = deal.get("company_en", "")
    round_name = deal.get("round", "")
    amount = deal.get("amount", "")
    investors = "、".join(deal.get("investors", []))
    intro = deal.get("company_intro", "暂无公司简介")
    tags = deal.get("industry_tags", [])
    related = deal.get("related_articles", [])
    history = deal.get("funding_history", [])

    # 构建 tags_html
    tags_html = " ".join([
        f'<span class="bg-indigo-50 text-indigo-600 text-xs px-2 py-0.5 rounded-full">{t}</span>'
        for t in tags
    ])

    # 构建 related_html
    related_html = ""
    for art in related[:5]:
        related_html += (
            f'<li><a href="{art.get("url", "#")}" target="_blank" '
            f'class="text-indigo-600 hover:underline">{art.get("title", "")}</a>'
            f' <span class="text-gray-400 text-xs">— {art.get("source", "")}</span></li>'
        )

    # 构建 history_html
    history_html = ""
    for h in history:
        h_investors = "、".join(h.get("investors", []))
        history_html += (
            f'<tr class="border-b border-gray-100">'
            f'<td class="py-2 px-3 text-sm font-medium">{h.get("round", "")}</td>'
            f'<td class="py-2 px-3 text-sm text-gray-500">{h.get("date", "")}</td>'
            f'<td class="py-2 px-3 text-sm font-semibold">{h.get("amount", "")}</td>'
            f'<td class="py-2 px-3 text-sm text-gray-500">{h_investors}</td>'
            f'</tr>'
        )

    # 提前构建可选 section（避免 f-string 嵌套）
    related_section = ""
    if related:
        related_section = (
            '  <div class="bg-white rounded-xl shadow-card p-6">\n'
            '    <h2 class="text-lg font-bold text-gray-900 mb-3">&#x1F4F0; 相关报道</h2>\n'
            f'    <ul class="space-y-2">{related_html}</ul>\n'
            '  </div>\n'
        )

    history_section = ""
    if history:
        history_section = (
            '  <div class="bg-white rounded-xl shadow-card p-6">\n'
            '    <h2 class="text-lg font-bold text-gray-900 mb-3">&#x1F4CB; 融资历史</h2>\n'
            '    <table class="w-full"><thead><tr class="text-xs text-gray-400 border-b">\n'
            '      <th class="py-2 px-3 text-left">轮次</th><th class="py-2 px-3 text-left">时间</th>\n'
            '      <th class="py-2 px-3 text-left">金额</th><th class="py-2 px-3 text-left">投资方</th>\n'
            '    </tr></thead><tbody>' + history_html + '</tbody></table>\n'
            '  </div>\n'
        )

    company_en_html = ""
    if company_en:
        company_en_html = f'<p class="text-sm text-gray-400 mb-3">{company_en}</p>\n'

    # 主 HTML 模板（单层 f-string，无嵌套）
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{company} - 融资详情 | AI 日报</title>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script>tailwind.config={{"theme":{{"extend":{{"fontFamily":{{"sans":["Inter","-apple-system","BlinkMacSystemFont","PingFang SC","sans-serif"]}}}}}}}}</script>
</head>
<body class="bg-gray-50 min-h-screen">
<nav class="sticky top-0 z-50 bg-white/85 backdrop-blur-md border-b border-gray-100">
  <div class="max-w-3xl mx-auto px-4 h-14 flex items-center">
    <a href="../../index.html" class="text-sm text-indigo-600 hover:text-indigo-700">← 返回日报</a>
    <span class="ml-4 font-bold text-gray-900">AI 日报 · 融资详情</span>
  </div>
</nav>
<main class="max-w-3xl mx-auto px-4 py-8 space-y-6">
  <div class="bg-white rounded-xl shadow-card p-6">
    <h1 class="text-2xl font-bold text-gray-900 mb-1">{company}</h1>
    {company_en_html}
    <div class="flex gap-2 mb-4">{tags_html}</div>
    <div class="grid grid-cols-3 gap-4 bg-gray-50 rounded-lg p-4">
      <div><p class="text-xs text-gray-400">融资轮次</p><p class="font-bold text-gray-900">{round_name}</p></div>
      <div><p class="text-xs text-gray-400">融资金额</p><p class="font-bold text-gray-900">{amount}</p></div>
      <div><p class="text-xs text-gray-400">投资方</p><p class="font-bold text-gray-900">{investors or "未披露"}</p></div>
    </div>
  </div>

  <div class="bg-white rounded-xl shadow-card p-6">
    <h2 class="text-lg font-bold text-gray-900 mb-3">&#x1F3E2; 公司简介</h2>
    <p class="text-sm text-gray-600 leading-relaxed">{intro}</p>
  </div>

{related_section}{history_section}</main>
</body>
</html>'''
