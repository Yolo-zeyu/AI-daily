"""
V2 微信推送脚本 — 使用 Server酱 API
适配 V2 的 learning dict 结构（concepts / deep_reads / videos / daily_question）
"""
import logging
import requests
from config import SERVERCHAN_SENDKEY, SITE_URL, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def push_wechat(date: str, news: list, deals: list, learning: dict) -> bool:
    """
    发送每日日报摘要到微信
    :param date: 日期字符串
    :param news: 新闻列表
    :param deals: 投融资列表
    :param learning: V2 学习内容 dict（含 concepts/deep_reads/videos/daily_question）
    :return: 是否推送成功
    """
    if not SERVERCHAN_SENDKEY:
        logger.warning("SERVERCHAN_SENDKEY 未配置，跳过微信推送")
        return False

    title, content = _build_message(date, news, deals, learning)
    return _send(title, content)


def _build_message(date: str, news: list, deals: list, learning: dict) -> tuple[str, str]:
    """构建 V2 推送消息内容（Markdown 格式）"""
    y, m, d = date.split("-")
    date_cn = f"{y}年{int(m)}月{int(d)}日"

    title = f"🤖 AI 日报 | {date}"

    lines = [f"# 🤖 AI 日报 | {date_cn}\n"]

    # ─── 今日要闻 ────────────────────────────────────
    lines.append("## 📰 今日要闻\n")
    for item in news[:5]:
        importance = "⭐" * min(item.get("importance", 3), 5)
        cat = item.get("category", "")
        cat_label = {"foundation-model": "大模型", "business": "融资", "tech-breakthrough": "技术",
                     "product": "产品", "policy": "政策", "opinion": "观点"}.get(cat, "")
        cat_tag = f"[{cat_label}] " if cat_label else ""
        lines.append(f"- {cat_tag}**[{item['title']}]({item['source_url']})** {importance} — {item['source']}")
    if not news:
        lines.append("- 暂无数据")
    lines.append("")

    # ─── 投融资速递 ──────────────────────────────────
    lines.append("## 💰 投融资速递\n")
    for item in deals[:3]:
        investors = "、".join(item.get("investors", []))
        inv_str = f"（{investors}）" if investors else ""
        lines.append(f"- **{item['company']}** 完成 **{item['round']}** {item['amount']}{inv_str}")
    if not deals:
        lines.append("- 暂无数据")
    lines.append("")

    # ─── 今日学习 ─────────────────────────────────────
    lines.append("## 📚 今日学习\n")

    # 核心概念
    concepts = learning.get("concepts", [])
    if concepts:
        lines.append("**📌 核心概念**\n")
        for c in concepts[:3]:
            diff = {"beginner": "入门", "intermediate": "进阶", "advanced": "高阶"}.get(c.get("difficulty"), "入门")
            lines.append(f"- **{c['concept']}**（{c.get('concept_en', '')}）{diff}：{c.get('definition', '')}")

    # 深度阅读
    deep_reads = learning.get("deep_reads", [])
    if deep_reads:
        lines.append("\n**📰 深度阅读**\n")
        for r in deep_reads[:2]:
            must = "🔥" if r.get("is_must_read") else "📖"
            lines.append(f"- {must} [{r['title']}]({r['url']}) — {r.get('source', '')}")

    # 每日一问
    daily_q = learning.get("daily_question", {})
    if daily_q.get("question"):
        lines.append(f"\n**💡 每日一问**：{daily_q['question']}")

    if not concepts and not deep_reads and not daily_q:
        lines.append("- 暂无学习内容")

    lines.append("")

    # ─── 链接 ────────────────────────────────────────
    if SITE_URL:
        lines.append(f"---\n🔗 [查看完整日报]({SITE_URL})")

    content = "\n".join(lines)
    return title, content


def _send(title: str, content: str, retry: int = 1) -> bool:
    """调用 Server酱 API 发送消息，失败重试一次"""
    url = f"https://sctapi.ftqq.com/{SERVERCHAN_SENDKEY}.send"
    for attempt in range(retry + 1):
        try:
            resp = requests.post(
                url,
                data={"title": title, "desp": content},
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    logger.info("微信推送成功")
                    return True
                else:
                    logger.warning(f"Server酱返回错误: {data}")
            else:
                logger.warning(f"Server酱 HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"推送请求异常 (第{attempt+1}次): {e}")

        if attempt < retry:
            import time
            time.sleep(3)

    logger.error("微信推送最终失败，跳过")
    return False
