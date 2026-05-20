"""
翻译工具模块
主：DeepL API
备：MyMemory API（免费，无需注册）
"""
import time
import requests
import logging
from config import DEEPL_API_KEY, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def translate_to_chinese(text: str) -> str:
    """将文本翻译为中文，优先使用 DeepL，失败则降级到 MyMemory"""
    if not text or not text.strip():
        return text

    # 主：DeepL
    if DEEPL_API_KEY:
        result = _deepl_translate(text)
        if result:
            return result
        logger.warning("DeepL 翻译失败，降级到 MyMemory")

    # 备：MyMemory
    result = _mymemory_translate(text)
    if result:
        return result

    logger.error("所有翻译方案均失败，返回原文")
    return text


def _deepl_translate(text: str) -> str | None:
    """调用 DeepL API 翻译"""
    try:
        # DeepL 免费版用 api-free.deepl.com，付费版用 api.deepl.com
        base_url = "https://api-free.deepl.com" if DEEPL_API_KEY.endswith(":fx") else "https://api.deepl.com"
        resp = requests.post(
            f"{base_url}/v2/translate",
            headers={"Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"},
            json={"text": [text], "target_lang": "ZH"},
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()["translations"][0]["text"]
        elif resp.status_code == 456:
            logger.warning("DeepL 免费额度已用完")
        else:
            logger.warning(f"DeepL 返回 {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"DeepL 请求异常: {e}")
    return None


def _mymemory_translate(text: str) -> str | None:
    """调用 MyMemory API 翻译（免费，限速 5000字符/天）"""
    try:
        resp = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text[:500], "langpair": "en|zh"},  # MyMemory 限制字符数
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("responseStatus") == 200:
                return data["responseData"]["translatedText"]
        logger.warning(f"MyMemory 返回异常: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"MyMemory 请求异常: {e}")
    return None


def batch_translate(items: list, field: str, delay: float = 1.0) -> list:
    """批量翻译列表中每个 item 的指定字段"""
    for item in items:
        text = item.get(field, "")
        if text and item.get("language") == "en":
            item[f"{field}_translated"] = translate_to_chinese(text)
            time.sleep(delay)  # 避免触发限速
    return items
