"""
配置文件 — V2 所有 API Key 和采集参数
通过环境变量注入，不要把真实 Key 提交到 git
"""
import os

# ─── API Keys ───────────────────────────────────────────────────────────────
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "")
SERVERCHAN_SENDKEY = os.getenv("SERVERCHAN_SENDKEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
SITE_URL = os.getenv("SITE_URL", "")

# ─── DeepSeek API ────────────────────────────────────────────────────────────
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# ─── 采集参数 ────────────────────────────────────────────────────────────────
MAX_NEWS_PER_SOURCE = 8       # 每个源最多取条数（V2 从 10 降到 8）
MAX_DEALS_PER_SOURCE = 15
MAX_LEARNING_CONCEPTS = 5
REQUEST_DELAY = 3             # V2: 3秒间隔，反爬礼仪
REQUEST_TIMEOUT = 15
USER_AGENTS = [               # V2: 随机 User-Agent 池
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]

# ─── 来源权威性排序（去重时保留优先级，越高越优先保留）───────────────────────────
SOURCE_AUTHORITY = {
    "TechCrunch": 14, "The Verge": 13, "Wired": 12, "MIT Technology Review": 11,
    "机器之心": 10, "36Kr": 9, "量子位": 8, "雷锋网": 7,
    "VentureBeat": 6, "极客公园": 5, "虎嗅": 4, "爱范儿": 3, "新智元": 2, "Hacker News": 1,
}

# ─── AI 关键词（投融资筛选用）────────────────────────────────────────────────
AI_KEYWORDS = [
    "AI", "人工智能", "大模型", "机器学习", "深度学习", "自然语言处理", "NLP",
    "计算机视觉", "CV", "自动驾驶", "智能驾驶", "机器人", "芯片", "GPU",
    "语言模型", "神经网络", "生成式", "智能体", "Agent", "RAG", "向量数据库",
    "具身智能", "多模态", "diffusion", "transformer",
]

# ─── 新闻分类体系 ────────────────────────────────────────────────────────────
NEWS_CATEGORIES = {
    "foundation-model": {"name": "大模型与基础模型", "icon": "🏢", "color": "#2563EB"},
    "business":         {"name": "融资与商业",       "icon": "💰", "color": "#EA580C"},
    "tech-breakthrough":{"name": "技术突破",         "icon": "🔬", "color": "#7C3AED"},
    "product":          {"name": "产品与应用",       "icon": "🛠️", "color": "#16A34A"},
    "policy":           {"name": "政策与监管",       "icon": "🏛️", "color": "#DC2626"},
    "opinion":          {"name": "行业观点",         "icon": "🌐", "color": "#6B7280"},
}

# ─── 数据源：新闻（V2 扩充到 14 个源）─────────────────────────────────────────
NEWS_SOURCES = [
    # 中文源
    {"name": "36Kr AI",          "url": "https://36kr.com/information/AI/",       "type": "scrape", "language": "zh", "priority": 2},
    {"name": "机器之心",         "url": "https://www.jiqizhixin.com/rss",          "type": "rss",     "language": "zh", "priority": 2},
    {"name": "量子位",           "url": "https://www.qbitai.com/",                 "type": "scrape",  "language": "zh", "priority": 3},
    {"name": "雷锋网",           "url": "https://www.leiphone.com/feed",           "type": "rss",     "language": "zh", "priority": 3},
    {"name": "极客公园",         "url": "https://www.geekpark.net/",               "type": "scrape",  "language": "zh", "priority": 4},
    {"name": "新智元",           "url": "https://rss.newrank.cc/v2/feed/5e4e5e5e5e5e5e5e5e5e5e5e", "type": "rss", "language": "zh", "priority": 4},
    {"name": "爱范儿",           "url": "https://www.ifanr.com/feed",              "type": "rss",     "language": "zh", "priority": 4},
    # 英文源
    {"name": "TechCrunch AI",    "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "type": "rss", "language": "en", "priority": 1},
    {"name": "The Verge AI",     "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "type": "rss", "language": "en", "priority": 1},
    {"name": "VentureBeat AI",   "url": "https://venturebeat.com/category/ai/feed/", "type": "rss",    "language": "en", "priority": 2},
    {"name": "Hacker News AI",   "url": "https://hn.algolia.com/api/v1/search?tags=story&query=artificial+intelligence&hitsPerPage=20", "type": "api", "language": "en", "priority": 3},
    {"name": "Wired AI",         "url": "https://www.wired.com/feed/tag/artificial-intelligence/latest/rss", "type": "rss", "language": "en", "priority": 2},
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/", "type": "rss", "language": "en", "priority": 1},
]

# ─── 数据源：投融资（V2 扩充）─────────────────────────────────────────────────
DEAL_SOURCES = [
    {"name": "36Kr 融资",       "url": "https://36kr.com/information/financing/",  "type": "scrape", "language": "zh", "priority": 0},
    {"name": "Crunchbase News", "url": "https://news.crunchbase.com/feed/",         "type": "rss",     "language": "en", "priority": 1},
    {"name": "TechCrunch Deals","url": "https://techcrunch.com/category/venture/feed/", "type": "rss", "language": "en", "priority": 1},
    {"name": "VentureBeat Deals","url": "https://venturebeat.com/category/venture-capital/feed/", "type": "rss", "language": "en", "priority": 2},
]
