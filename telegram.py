import httpx
import logging
from typing import List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8725608346:AAGZ8ddO1H5ul-DkOugsGnrgucel0tGrNRw"

# ============================================
# СПИСОК ПОЛЬЗОВАТЕЛЕЙ
# ============================================
USER_IDS = [
    "1400906997",
    "8938872167",
]

# ============================================
# ID КАНАЛА (ЗАМЕНИТЕ НА РЕАЛЬНЫЙ!)
# ============================================
CHANNEL_ID = "-1001234567890"  # 👈 ВСТАВЬТЕ СВОЙ ID КАНАЛА!

# ============================================
# ХРАНИЛИЩЕ ДЛЯ ОТПРАВЛЕННЫХ В КАНАЛ НОВОСТЕЙ
# ============================================
sent_to_channel = set()

# ============================================
# ФУНКЦИИ ДЛЯ КАНАЛА
# ============================================

async def send_photo_to_channel(image_url: Optional[str], caption: str, url: str = ""):
    """Отправка фото в канал"""
    if image_url:
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    json={
                        "chat_id": CHANNEL_ID,
                        "photo": image_url,
                        "caption": caption[:1000],
                        "parse_mode": "HTML"
                    }
                )
                if r.status_code == 200:
                    logger.info(f"✅ Photo sent to channel")
                    if url:
                        sent_to_channel.add(url)
                    return r.json()
                else:
                    logger.warning(f"sendPhoto to channel failed: {r.status_code}")
        except Exception as e:
            logger.error(f"sendPhoto to channel exception: {e}")
    
    # Если нет фото - отправляем текст
    return await send_text_to_channel(caption, url)

async def send_text_to_channel(text: str, url: str = ""):
    """Отправка текста в канал"""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": CHANNEL_ID,
                    "text": text,
                    "parse_mode": "HTML"
                }
            )
            if r.status_code == 200:
                logger.info(f"✅ Text sent to channel")
                if url:
                    sent_to_channel.add(url)
            return r.json()
    except Exception as e:
        logger.error(f"Error sending to channel: {e}")
        return {"error": str(e)}

# ============================================
# ФУНКЦИИ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ
# ============================================

async def send_photo_to_user(user_id: str, image_url: Optional[str], caption: str):
    """Отправка фото пользователю"""
    result = {"photo": None, "text": None}
    
    if image_url:
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    json={
                        "chat_id": user_id,
                        "photo": image_url,
                        "caption": caption[:1000],
                        "parse_mode": "HTML"
                    }
                )
                result["photo"] = {"status": r.status_code, "body": r.json()}
                if r.status_code == 200:
                    logger.info(f"✅ Photo sent to {user_id}")
                    return result
        except Exception as e:
            result["photo"] = {"error": str(e)}
            logger.error(f"sendPhoto exception for {user_id}: {e}")
    
    # Фолбэк на текст
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": user_id, "text": caption, "parse_mode": "HTML"}
            )
            result["text"] = {"status": r.status_code, "body": r.json()}
    except Exception as e:
        result["text"] = {"error": str(e)}
    
    return result

async def send_text_to_user(user_id: str, text: str):
    """Отправка текста пользователю"""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": user_id, "text": text, "parse_mode": "HTML"}
            )
            return r.json()
    except Exception as e:
        return {"error": str(e)}

# ============================================
# ОСНОВНЫЕ ФУНКЦИИ (для совместимости)
# ============================================

async def send_photo(image_url: Optional[str], caption: str):
    """Отправка фото ВСЕМ пользователям"""
    results = {}
    for user_id in USER_IDS:
        result = await send_photo_to_user(user_id, image_url, caption)
        results[user_id] = result
    return results.get(USER_IDS[0], {})

async def send_text(text: str):
    """Отправка текста ВСЕМ пользователям"""
    results = {}
    for user_id in USER_IDS:
        result = await send_text_to_user(user_id, text)
        results[user_id] = result
    return results.get(USER_IDS[0], {})

# ============================================
# ОСНОВНАЯ ФУНКЦИЯ - ДЛЯ ПОЛЬЗОВАТЕЛЕЙ (каждые 30 мин)
# ============================================

async def notify_if_important(item):
    """Отправка новости пользователям (каждые 30 минут)"""
    title = item.get('title', 'Новость')[:100]
    url = item.get('url', '')
    source = item.get('source', 'неизвестный источник')
    
    # Формируем сообщение
    caption = f"📰 <b>{title}</b>\n\n"
    caption += f"📰 Источник: {source}\n"
    caption += f"\n🔗 <a href='{url}'>Подробнее</a>"
    
    image_url = item.get("image_url", "")
    
    # Отправляем ВСЕМ пользователям
    for user_id in USER_IDS:
        if image_url:
            await send_photo_to_user(user_id, image_url, caption)
        else:
            await send_text_to_user(user_id, caption)
    
    logger.info(f"✅ News sent to {len(USER_IDS)} users: {title[:30]}...")

# ============================================
# ФУНКЦИЯ ДЛЯ КАНАЛА (каждые 2 часа)
# ============================================

async def send_to_channel(item):
    """Отправка в канал (только с фото, каждые 2 часа)"""
    title = item.get('title', 'Новость')[:100]
    url = item.get('url', '')
    source = item.get('source', 'неизвестный источник')
    image_url = item.get("image_url", "")
    
    # Проверяем, не отправляли ли уже эту новость
    if url in sent_to_channel:
        logger.info(f"⏭️ Already sent to channel: {title[:30]}")
        return
    
    # Проверяем, есть ли фото
    if not image_url:
        logger.info(f"⏭️ No image, skipping channel: {title[:30]}")
        return
    
    # Формируем сообщение для канала
    caption = f"📰 <b>{title}</b>\n\n"
    caption += f"📰 Источник: {source}\n"
    caption += f"🔗 <a href='{url}'>Подробнее</a>"
    
    # Отправляем в канал
    await send_photo_to_channel(image_url, caption, url)
    logger.info(f"✅ News sent to channel: {title[:30]}")

# ============================================
# ПРИВЕТСТВИЕ
# ============================================

async def send_start_message():
    """Приветствие в канал и пользователям"""
    message = "🤖 <b>News Bot запущен!</b>\n\n"
    message += "✅ Бот активен\n"
    message += "📰 В канал: каждые 2 часа\n"
    message += "💬 В личку: каждые 30 минут"
    
    # В канал
    await send_text_to_channel(message)
    
    # Всем пользователям
    for user_id in USER_IDS:
        await send_text_to_user(user_id, message)

print(f"🤖 Бот настроен для {len(USER_IDS)} пользователей и канала")
print(f"📢 ID канала: {CHANNEL_ID}")
