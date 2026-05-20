"""
V2 翻译工具模块
主：DeepL API
备1：DeepSeek API（用大模型翻译）
备2：MyMemory API（免费，无需注册）
"""
import time
import requests
import logging
from config import DEEPL_API_KEY, DEEPSEEK_API_KEY, DEEPSEEK_API_URL, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def translate_to_chinese(text: str) -> str:
    """将文本翻译为中文，优先使用 DeepL，失败依次降级"""
    if not text or not text.strip():
        return text

    # 主：DeepL
    if DEEPL_API_KEY:
        result = _deepl_translate(text)
        if result:
            return result
        logger.warning("DeepL 翻译失败，降级到 DeepSeek")

    # 备1：DeepSeek
    if DEEPSEEK_API_KEY:
        result = _deepseek_translate(text)
        if result:
            return result
        logger.warning("DeepSeek 翻译失败，降级到 MyMemory")

    # 备2：MyMemory
    result = _mymemory_translate(text)
    if result:
        return result

    logger.error("所有翻译方案均失败，返回原文")
    return text


def _deepl_translate(text: str) -> str | None:
    """调用 DeepL API 翻译"""
    try:
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


def _deepseek_translate(text: str) -> str | None:
    """调用 DeepSeek API 翻译（V2 新增兜底方案）"""
    try:
        resp = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个专业翻译，将英文翻译为简洁流畅的中文。只输出翻译结果，不要解释。"},
                    {"role": "user", "content": text[:2000]},
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
            },
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()["choices"][0]["message"]["content"].strip()
        return result if result else None
    except Exception as e:
        logger.warning(f"DeepSeek 翻译异常: {e}")
    return None


def _mymemory_translate(text: str) -> str | None:
    """调用 MyMemory API 翻译（免费，限速 5000字符/天）"""
    try:
        resp = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text[:500], "langpair": "en|zh"},
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


def batch_translate(items: list, field: str = "summary", delay: float = 1.0) -> list:
    """
    V2 批量翻译：对英文条目的指定字段翻译为中文
    支持多字段翻译：field 可以是 "summary" 或 "title" 或逗号分隔的多字段
    """
    fields = [f.strip() for f in field.split(",")]

    for item in items:
        if item.get("language") != "en":
            continue

        for f in fields:
            text = item.get(f, "")
            if text and not item.get(f"{f}_translated"):
                translated = translate_to_chinese(text)
                if translated and translated != text:
                    item[f"{f}_translated"] = translated
                time.sleep(delay)

    return items
