import httpx
import logging
from typing import List, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8725608346:AAGZ8ddO1H5ul-DkOugsGnrgucel0tGrNRw"

# ============================================
# СПИСОК ВСЕХ ПОЛЬЗОВАТЕЛЕЙ
# ============================================
USER_IDS = [
    "1400906997",   # Первый пользователь
    "8938872167",   # Второй пользователь (НОВЫЙ!)
    # Добавляйте новых сюда
]

# Для обратной совместимости (если где-то используется USER_ID)
USER_ID = USER_IDS[0]

# ============================================
# ФУНКЦИИ ДЛЯ ОТПРАВКИ ОДНОМУ ПОЛЬЗОВАТЕЛЮ
# ============================================

async def send_photo_to_user(user_id: str, image_url: Optional[str], caption: str):
    """Отправка фото конкретному пользователю"""
    result = {"photo": None, "text": None}
    
    if image_url:
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    json={
                        "chat_id": user_id,
                        "photo": image_url,
                        "caption": caption[:1000]
                    }
                )
                result["photo"] = {"status": r.status_code, "body": r.json()}
                if r.status_code == 200 and r.json().get("ok"):
                    logger.info(f"✅ Photo sent to {user_id}")
                    return result
                logger.warning(f"sendPhoto to {user_id} failed: {r.status_code}")
        except Exception as e:
            result["photo"] = {"error": str(e)}
            logger.error(f"sendPhoto exception for {user_id}: {e}")
    
    # Фолбэк на текст
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": user_id, "text": caption}
            )
            result["text"] = {"status": r.status_code, "body": r.json()}
            if r.status_code == 200:
                logger.info(f"✅ Text sent to {user_id}")
    except Exception as e:
        result["text"] = {"error": str(e)}
        logger.error(f"sendText exception for {user_id}: {e}")
    
    return result

async def send_text_to_user(user_id: str, text: str):
    """Отправка текста конкретному пользователю"""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": user_id, "text": text}
            )
            if r.status_code == 200:
                logger.info(f"✅ Text sent to {user_id}")
            else:
                logger.error(f"Failed to send to {user_id}: {r.status_code}")
            return r.json()
    except Exception as e:
        logger.error(f"Error sending to {user_id}: {e}")
        return {"error": str(e)}

# ============================================
# ОСНОВНЫЕ ФУНКЦИИ (отправляют ВСЕМ)
# ============================================

async def send_photo(image_url: Optional[str], caption: str):
    """Отправка фото ВСЕМ пользователям"""
    results = {}
    
    for user_id in USER_IDS:
        logger.info(f"📤 Sending photo to user {user_id}")
        result = await send_photo_to_user(user_id, image_url, caption)
        results[user_id] = result
    
    # Возвращаем результат для первого пользователя
    return results.get(USER_ID, {})

async def send_text(text: str):
    """Отправка текста ВСЕМ пользователям"""
    results = {}
    
    for user_id in USER_IDS:
        logger.info(f"📤 Sending text to user {user_id}")
        result = await send_text_to_user(user_id, text)
        results[user_id] = result
    
    # Возвращаем результат для первого пользователя
    return results.get(USER_ID, {})

# ============================================
# ОСНОВНАЯ ФУНКЦИЯ ДЛЯ ОТПРАВКИ НОВОСТЕЙ
# ============================================

async def notify_if_important(item):
    """Отправка новости ВСЕМ пользователям"""
    caption = f"✨ {item.get('title','')}\n{item.get('url','')}\n— {item.get('source','')}"
    image_url = item.get("image_url", "")
    
    # Отправляем ВСЕМ пользователям
    await send_photo(image_url, caption)
    
    logger.info(f"✅ News sent to {len(USER_IDS)} users: {item.get('title', '')[:30]}...")

# ============================================
# ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

async def send_start_message():
    """Приветственное сообщение ВСЕМ пользователям"""
    message = "🤖 News Bot запущен!\n\n"
    message += "✅ Бот активен и готов к работе\n"
    message += f"👥 Пользователей: {len(USER_IDS)}\n"
    message += "📰 Новости будут приходить автоматически"
    
    for user_id in USER_IDS:
        await send_text_to_user(user_id, message)
        logger.info(f"✅ Startup message sent to {user_id}")

def get_users() -> List[str]:
    """Получить список всех пользователей"""
    return USER_IDS.copy()

def add_user(user_id: str) -> bool:
    """Добавить нового пользователя"""
    if user_id not in USER_IDS:
        USER_IDS.append(user_id)
        logger.info(f"✅ User {user_id} added")
        return True
    return False

def remove_user(user_id: str) -> bool:
    """Удалить пользователя"""
    if user_id in USER_IDS:
        USER_IDS.remove(user_id)
        logger.info(f"User {user_id} removed")
        return True
    return False

# ============================================
# ПРИ ЗАПУСКЕ МОДУЛЯ
# ============================================

print(f"🤖 Бот настроен для {len(USER_IDS)} пользователей:")
for uid in USER_IDS:
    print(f"   - {uid}")
