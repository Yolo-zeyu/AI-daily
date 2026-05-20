# AI 日报

每日自动聚合 AI 行业新闻、投融资动态和学习内容，部署在 GitHub Pages，微信推送摘要。

## 功能

- 📰 **今日要闻**：聚合 36Kr、机器之心、量子位、Hacker News、The Verge 等多源 AI 新闻
- 💰 **投融资速递**：每日 AI 领域融资动态
- 📚 **今日学习**：AI 以后从当日新闻提取概念，生成通俗学习卡片
- 📱 **微信推送**：每天早上 8:00 推送摘要（Server酱）

## 快速开始

### 1. Fork 仓库

### 2. 配置 GitHub Secrets

在 Settings → Secrets and variables → Actions 中添加：

| 变量名 | 说明 | 是否必须 |
|--------|------|----------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key，用于生成学习内容 | 推荐 |
| `SERVERCHAN_SENDKEY` | Server酱 SendKey，用于微信推送 | 可选 |
| `DEEPL_API_KEY` | DeepL API Key，用于翻译英文内容 | 可选 |
| `SITE_URL` | 部署后的网页 URL，用于推送中的链接 | 可选 |

### 3. 启用 GitHub Pages

Settings → Pages → Source 选择 `main` 分支根目录

### 4. 手动触发第一次更新

Actions → AI Daily Update → Run workflow

## 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量（可选）
export DEEPSEEK_API_KEY="sk-xxx"
export SERVERCHAN_SENDKEY="xxx"

# 运行
cd scripts
python main.py
```

## 项目结构

```
ai-daily/
├── .github/workflows/daily.yml   # 定时任务
├── data/                         # 每日 JSON 数据
├── scripts/                      # Python 采集脚本
│   ├── main.py                   # 主入口
│   ├── config.py                 # 配置
│   ├── fetch_news.py             # 新闻采集
│   ├── fetch_deals.py            # 投融资采集
│   ├── generate_learning.py      # 学习内容生成
│   ├── translate.py              # 翻译
│   └── push_wechat.py            # 微信推送
├── js/app.js                     # 前端交互
├── index.html                    # 日报网页
└── requirements.txt
```

## 数据来源

- 36Kr AI 频道 / 融资频道
- 机器之心
- 量子位
- Hacker News（AI 标签）
- The Verge AI
- Crunchbase News

内容版权归原作者所有，本站仅做聚合展示。
