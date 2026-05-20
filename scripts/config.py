"""
配置文件 — 所有 API Key 和采集参数
通过环境变量注入，不要把真实 Key 提交到 git
"""
import os

# ─── API Keys ───────────────────────────────────────────────────────────────
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "")
SERVERCHAN_SENDKEY = os.getenv("SERVERCHAN_SENDKEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
SITE_URL = os.getenv("SITE_URL", "")

# ─── 采集参数 ────────────────────────────────────────────────────────────────
MAX_NEWS_PER_SOURCE = 10
MAX_DEALS_PER_SOURCE = 15
MAX_LEARNING_CONCEPTS = 5
REQUEST_DELAY = 2        # 每次请求间隔（秒），爬虫礼仪
REQUEST_TIMEOUT = 15     # 请求超时（秒）
USER_AGENT = "Mozilla/5.0 (compatible; AIDailyBot/1.0; +https://github.com/ai-daily)"

# ─── AI 关键词（投融资筛选用）────────────────────────────────────────────────
AI_KEYWORDS = [
    "AI", "人工智能", "大模型", "机器学习", "深度学习", "自然语言处理", "NLP",
    "计算机视觉", "CV", "自动驾驶", "智能驾驶", "机器人", "芯片", "GPU",
    "语言模型", "神经网络", "生成式", "智能体", "Agent", "RAG", "向量数据库",
    "具身智能", "多模态", "diffusion", "transformer",
]

# ─── 数据源 ──────────────────────────────────────────────────────────────────
NEWS_SOURCES = [
    {
        "name": "36Kr AI",
        "url": "https://36kr.com/information/AI/",
        "type": "scrape",
        "language": "zh",
        "priority": 0,
    },
    {
        "name": "机器之心",
        "url": "https://www.jiqizhixin.com/rss",
        "type": "rss",
        "language": "zh",
        "priority": 0,
    },
    {
        "name": "Hacker News AI",
        "url": "https://hn.algolia.com/api/v1/search?tags=story&query=artificial+intelligence&hitsPerPage=20",
        "type": "api",
        "language": "en",
        "priority": 1,
    },
    {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
        "type": "rss",
        "language": "en",
        "priority": 1,
    },
    {
        "name": "量子位",
        "url": "https://www.qbitai.com/",
        "type": "scrape",
        "language": "zh",
        "priority": 2,
    },
]

DEAL_SOURCES = [
    {
        "name": "36Kr 融资",
        "url": "https://36kr.com/information/financing/",
        "type": "scrape",
        "language": "zh",
        "priority": 0,
    },
    {
        "name": "Crunchbase News",
        "url": "https://news.crunchbase.com/feed/",
        "type": "rss",
        "language": "en",
        "priority": 1,
    },
]
