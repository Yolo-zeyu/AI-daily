"""
主入口脚本 — 串联所有模块，生成每日日报
执行流程：
1. 采集新闻
2. 采集投融资
3. 翻译英文内容
4. 生成学习内容
5. 合并数据，保存 JSON
6. 微信推送
"""
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 确保 scripts/ 下的模块可以互相 import
sys.path.insert(0, str(Path(__file__).parent))

from fetch_news import fetch_all_news
from fetch_deals import fetch_all_deals
from generate_learning import generate_learning
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
    logger.info(f"=== AI 日报生成开始 | {today_str} ===")

    # 1. 采集新闻
    logger.info("Step 1: 采集新闻")
    news = fetch_all_news()
    logger.info(f"新闻采集完成，共 {len(news)} 条")

    # 2. 采集投融资
    logger.info("Step 2: 采集投融资")
    deals = fetch_all_deals()
    logger.info(f"投融资采集完成，共 {len(deals)} 条")

    # 3. 翻译英文内容
    logger.info("Step 3: 翻译英文内容")
    news = batch_translate(news, "summary")
    logger.info("翻译完成")

    # 4. 生成学习内容
    logger.info("Step 4: 生成学习内容")
    learning = generate_learning(news)
    logger.info(f"学习内容生成完成，共 {len(learning)} 个概念")

    # 5. 合并数据并保存 JSON
    logger.info("Step 5: 保存数据")
    data = {
        "date": today_str,
        "generated_at": datetime.now(CST).isoformat(),
        "news": news,
        "deals": deals,
        "learning": learning,
    }
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    output_path = data_dir / f"{today_str}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"数据已保存到 {output_path}")

    # 6. 微信推送
    logger.info("Step 6: 微信推送")
    push_wechat(today_str, news, deals, learning)

    logger.info(f"=== AI 日报生成完成 | {today_str} ===")
    logger.info(f"新闻 {len(news)} 条 | 投融资 {len(deals)} 条 | 学习概念 {len(learning)} 个")


if __name__ == "__main__":
    main()
