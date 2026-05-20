"""
V2 主入口脚本 — 串联所有模块，生成每日日报
执行流程（10步）：
1. 采集新闻（多源）
2. 采集投融资
3. AI 分类 + 评级
4. 翻译英文内容
5. 封面图提取
6. 生成学习内容（4个子板块）
7. 生成融资详情页
8. 合并数据，保存 JSON
9. 推送微信
"""
import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 确保 scripts/ 下的模块可以互相 import
sys.path.insert(0, str(Path(__file__).parent))

from fetch_news import fetch_all_news, extract_cover_image
from fetch_deals import fetch_all_deals
from classify_news import classify_all_news
from generate_learning import generate_learning
from generate_deal_pages import generate_deal_pages
from translate import batch_translate
from push_wechat import push_wechat

# ─── 日志配置 ─────────────────────────────────────────────────────────────────
CST = timezone(timedelta(hours=8))
today_str = datetime.now(CST).strftime("%Y-%m-%d")

log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / f"{today_str}.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")


def main():
    base_dir = str(Path(__file__).parent.parent)
    logger.info(f"=== AI 日报生成开始 | {today_str} ===")

    # 1. 采集新闻（多源）
    logger.info("Step 1: 采集新闻")
    news = fetch_all_news()
    logger.info(f"新闻采集完成，共 {len(news)} 条")

    # 2. 采集投融资
    logger.info("Step 2: 采集投融资")
    deals = fetch_all_deals()
    logger.info(f"投融资采集完成，共 {len(deals)} 条")

    # 3. AI 分类 + 评级
    logger.info("Step 3: AI 分类 + 评级")
    news = classify_all_news(news)
    logger.info("分类完成")

    # 4. 翻译英文内容
    logger.info("Step 4: 翻译英文内容")
    news = batch_translate(news, "summary")
    logger.info("翻译完成")

    # 5. 封面图提取（对没有封面图的新闻，尝试从原文URL提取）
    logger.info("Step 5: 封面图提取")
    cover_count = 0
    for item in news:
        if not item.get("cover_image"):
            url = item.get("source_url", "")
            if not url or not url.startswith("http"):
                continue
            try:
                cover = extract_cover_image(url)
                if cover:
                    item["cover_image"] = cover
                    cover_count += 1
            except Exception as e:
                logger.debug(f"封面图提取异常 ({url}): {e}")
            import time; time.sleep(0.5)  # 礼貌延迟
    logger.info(f"封面图提取完成，新增 {cover_count} 张（共 {len(news)} 条新闻，{len(news) - cover_count} 条无图将使用占位图）")

    # 6. 生成学习内容（4个子板块）
    logger.info("Step 6: 生成学习内容")
    learning = generate_learning(news, deals)
    logger.info("学习内容生成完成")

    # 7. 生成融资详情页
    logger.info("Step 7: 生成融资详情页")
    deals = generate_deal_pages(deals, news, base_dir)
    logger.info("融资详情页生成完成")

    # 8. 合并数据并保存 JSON
    logger.info("Step 8: 保存数据")
    data = {
        "date": today_str,
        "generated_at": datetime.now(CST).isoformat(),
        "news": news,
        "deals": deals,
        "learning": learning,
    }
    data_dir = Path(base_dir) / "data"
    data_dir.mkdir(exist_ok=True)
    output_path = data_dir / f"{today_str}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"数据已保存到 {output_path}")

    # 9. 微信推送
    logger.info("Step 9: 微信推送")
    push_wechat(today_str, news, deals, learning)

    logger.info(f"=== AI 日报生成完成 | {today_str} ===")
    news_count = len(news)
    deals_count = len(deals)
    concepts_count = len(learning.get("concepts", []))
    logger.info(f"新闻 {news_count} 条 | 投融资 {deals_count} 条 | 学习概念 {concepts_count} 个")


if __name__ == "__main__":
    main()
