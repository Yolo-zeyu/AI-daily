"""
微信推送脚本 — 使用 Server酱 API
免费版：每天最多 5 条消息，完全够用
注册地址：https://sct.ftqq.com
"""
import logging
import requests
from config import SERVERCHAN_SENDKEY, SITE_URL, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def push_wechat(date: str, news: list, deals: list, learning: list) -> bool:
    """
    发送每日日报摘要到微信
    :param date: 日期字符串，如 "2026-05-20"
    :param news: 新闻列表
    :param deals: 投融资列表
    :param learning: 学习内容列表
    :return: 是否推送成功
    """
    if not SERVERCHAN_SENDKEY:
        logger.warning("SERVERCHAN_SENDKEY 未配置，跳过微信推送")
        return False

    title, content = _build_message(date, news, deals, learning)
    return _send(title, content)


def _build_message(date: str, news: list, deals: list, learning: list) -> tuple[str, str]:
    """构建推送消息内容（Markdown 格式）"""
    y, m, d = date.split("-")
    date_cn = f"{y}年{int(m)}月{int(d)}日"

    title = f"🤖 AI 日报 | {date}"

    lines = [f"# 🤖 AI 日报 | {date_cn}\n"]

    # 今日要闻
    lines.append("## 📰 今日要闻\n")
    for item in news[:5]:
        lines.append(f"- **[{item['title']}]({item['source_url']})** — {item['source']}")
    if not news:
        lines.append("- 暂无数据")
    lines.append("")

    # 投融资速递
    lines.append("## 💰 投融资速递\n")
    for item in deals[:3]:
        investors = "、".join(item.get("investors", []))
        inv_str = f"（{investors}）" if investors else ""
        lines.append(f"- **{item['company']}** 完成 **{item['round']}** {item['amount']}{inv_str}")
    if not deals:
        lines.append("- 暂无数据")
    lines.append("")

    # 今日学习
    lines.append("## 📚 今日学习\n")
    for item in learning[:3]:
        lines.append(f"- **{item['concept']}**（{item['concept_en']}）：{item['definition']}")
    if not learning:
        lines.append("- 暂无数据")
    lines.append("")

    # 链接
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
