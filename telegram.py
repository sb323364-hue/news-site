# telegram_bot.py - полная версия

import httpx
import asyncio
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = "8725608346:AAGZ8ddO1H5ul-DkOugsGnrgucel0tGrNRw"
USER_ID = "1400906997"

# База данных для истории
class BotDatabase:
    def __init__(self, db_path="bot_history.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.init_db()
    
    def init_db(self):
        """Создание таблиц"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                url TEXT UNIQUE,
                source TEXT,
                sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                importance REAL DEFAULT 0
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                news_url TEXT,
                feedback TEXT,  -- 'like' or 'dislike'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def is_news_sent(self, url):
        """Проверка, отправлялась ли новость ранее"""
        self.cursor.execute('SELECT id FROM sent_news WHERE url = ?', (url,))
        return self.cursor.fetchone() is not None
    
    def save_sent_news(self, title, url, source, importance):
        """Сохранение отправленной новости"""
        self.cursor.execute('''
            INSERT OR IGNORE INTO sent_news (title, url, source, importance)
            VALUES (?, ?, ?, ?)
        ''', (title, url, source, importance))
        self.conn.commit()
    
    def save_feedback(self, url, feedback):
        """Сохранение отзыва пользователя"""
        self.cursor.execute('''
            INSERT INTO user_feedback (news_url, feedback)
            VALUES (?, ?)
        ''', (url, feedback))
        self.conn.commit()
    
    def get_stats(self):
        """Получение статистики"""
        total = self.cursor.execute('SELECT COUNT(*) FROM sent_news').fetchone()[0]
        likes = self.cursor.execute("SELECT COUNT(*) FROM user_feedback WHERE feedback = 'like'").fetchone()[0]
        dislikes = self.cursor.execute("SELECT COUNT(*) FROM user_feedback WHERE feedback = 'dislike'").fetchone()[0]
        return {'total': total, 'likes': likes, 'dislikes': dislikes}

db = BotDatabase()

# Расширенный класс бота
class NewsBot:
    def __init__(self, token, user_id):
        self.token = token
        self.user_id = user_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.stats = {'sent': 0, 'errors': 0}
    
    async def send_photo(self, image_url: Optional[str], caption: str) -> Dict:
        """Отправка фото с поддержкой fallback"""
        result = {"photo": None, "text": None}
        
        # Пытаемся отправить фото
        if image_url:
            try:
                async with httpx.AsyncClient(timeout=15) as c:
                    r = await c.post(
                        f"{self.base_url}/sendPhoto",
                        json={
                            "chat_id": self.user_id,
                            "photo": image_url,
                            "caption": caption[:1000],
                            "parse_mode": "HTML"
                        }
                    )
                    result["photo"] = {"status": r.status_code, "body": r.json()}
                    if r.status_code == 200 and r.json().get("ok"):
                        self.stats['sent'] += 1
                        return result
                    logger.error(f"sendPhoto failed: {r.status_code} {r.text}")
            except Exception as e:
                result["photo"] = {"error": str(e)}
                logger.error(f"sendPhoto exception: {e}")
        
        # Fallback на текст
        result["text"] = await self.send_text(caption)
        return result
    
    async def send_text(self, text: str, parse_mode: str = "HTML") -> Dict:
        """Отправка текстового сообщения"""
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(
                    f"{self.base_url}/sendMessage",
                    json={
                        "chat_id": self.user_id,
                        "text": text,
                        "parse_mode": parse_mode
                    }
                )
                return {"status": r.status_code, "body": r.json()}
        except Exception as e:
            logger.error(f"sendText exception: {e}")
            return {"error": str(e)}
    
    async def send_news(self, item: Dict, importance_threshold: float = 0.5):
        """Умная отправка новостей"""
        # Проверка на дубликаты
        if db.is_news_sent(item.get('url')):
            logger.info(f"News already sent: {item.get('title')}")
            return
        
        # Рассчет важности
        importance = self.calculate_importance(item)
        if importance < importance_threshold:
            logger.info(f"Skipped (importance {importance}): {item.get('title')}")
            return
        
        # Формирование сообщения
        caption = self.format_news_message(item, importance)
        image_url = item.get("image_url", "")
        
        # Отправка
        result = await self.send_photo(image_url, caption)
        
        # Сохранение в истории
        if result.get('photo', {}).get('status') == 200 or result.get('text', {}).get('status') == 200:
            db.save_sent_news(
                item.get('title', ''),
                item.get('url', ''),
                item.get('source', ''),
                importance
            )
    
    def calculate_importance(self, item: Dict) -> float:
        """Расчет важности новости"""
        importance = 0.0
        
        # 1. Ключевые слова
        important_keywords = [
            'срочно', 'важно', 'кризис', 'выборы', 'война', 
            'экономика', 'политика', 'новый', 'первый', 'рекорд'
        ]
        title = item.get('title', '').lower()
        for keyword in important_keywords:
            if keyword in title:
                importance += 0.15
        
        # 2. Источник
        important_sources = ['tass', 'rbc', 'interfax', 'ria']
        if any(s in item.get('source', '').lower() for s in important_sources):
            importance += 0.2
        
        # 3. Длина заголовка (краткие новости часто важнее)
        if len(title) < 60:
            importance += 0.1
        
        # 4. Наличие ключевых слов в описании
        content = item.get('content', '').lower()
        if any(kw in content for kw in important_keywords):
            importance += 0.1
        
        # 5. Категория
        important_categories = ['политика', 'экономика', 'происшествия']
        if item.get('category') in important_categories:
            importance += 0.2
        
        return min(importance, 1.0)
    
    def format_news_message(self, item: Dict, importance: float) -> str:
        """Форматирование сообщения для отправки"""
        # Выбор эмодзи в зависимости от важности
        if importance > 0.8:
            emoji = "🔴"
        elif importance > 0.6:
            emoji = "🟠"
        else:
            emoji = "🟡"
        
        # Категория
        category = item.get('category', 'другое')
        category_emojis = {
            'политика': '🏛️',
            'экономика': '💰',
            'технологии': '💻',
            'спорт': '⚽',
            'культура': '🎭',
            'происшествия': '🚨'
        }
        category_emoji = category_emojis.get(category, '📰')
        
        # Формирование
        message = f"{emoji} <b>{item.get('title', '')}</b>\n\n"
        message += f"{category_emoji} Категория: <b>{category}</b>\n"
        message += f"📊 Важность: <b>{int(importance * 100)}%</b>\n"
        message += f"📰 Источник: <b>{item.get('source', 'неизвестен')}</b>\n"
        
        # Добавляем краткое содержание, если есть
        content = item.get('content', '')
        if content:
            message += f"\n📝 {content[:200]}...\n"
        
        message += f"\n🔗 <a href='{item.get('url', '')}'>Читать полностью</a>\n"
        message += f"\n🔄 <i>Новость {item.get('date', '')}</i>"
        
        # Добавляем кнопки для обратной связи (будут обрабатываться в следующем обновлении)
        message += f"\n\n👍 <b>Нравится?</b> Оценивайте!"
        
        return message
    
    async def send_digest(self, news_list: List[Dict], title: str = "📰 Дайджест новостей"):
        """Отправка дайджеста"""
        if not news_list:
            await self.send_text("📭 Новостей пока нет")
            return
        
        message = f"<b>{title}</b>\n\n"
        for i, item in enumerate(news_list[:10], 1):
            importance = self.calculate_importance(item)
            emoji = "🔴" if importance > 0.8 else "🟠" if importance > 0.6 else "🟡"
            message += f"{i}. {emoji} <b>{item.get('title', '')[:60]}</b>\n"
            message += f"   📰 {item.get('source', '')} | ⭐ {int(importance * 100)}%\n"
            message += f"   🔗 <a href='{item.get('url', '')}'>Подробнее</a>\n\n"
        
        await self.send_text(message)
    
    async def send_statistics(self):
        """Отправка статистики"""
        stats = db.get_stats()
        message = f"📊 <b>Статистика бота</b>\n\n"
        message += f"📰 Отправлено новостей: <b>{stats['total']}</b>\n"
        message += f"👍 Понравилось: <b>{stats['likes']}</b>\n"
        message += f"👎 Не понравилось: <b>{stats['dislikes']}</b>\n"
        message += f"🔄 Активность: {datetime.now().strftime('%H:%M')}"
        
        await self.send_text(message)
    
    async def interactive_menu(self):
        """Интерактивное меню (кнопки)"""
        keyboard = [
            [
                {"text": "📰 Последние новости", "callback_data": "latest"},
                {"text": "⭐ Популярное", "callback_data": "popular"}
            ],
            [
                {"text": "🔍 Поиск", "callback_data": "search"},
                {"text": "📊 Статистика", "callback_data": "stats"}
            ],
            [
                {"text": "⚙️ Настройки", "callback_data": "settings"}
            ]
        ]
        
        await self.send_inline_keyboard(
            text="👋 Привет! Я бот-агрегатор новостей.\n\nВыберите действие:",
            keyboard=keyboard
        )
    
    async def send_inline_keyboard(self, text: str, keyboard: List[List[Dict]]):
        """Отправка сообщения с инлайн-кнопками"""
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(
                    f"{self.base_url}/sendMessage",
                    json={
                        "chat_id": self.user_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "reply_markup": {
                            "inline_keyboard": keyboard
                        }
                    }
                )
                return r.json()
        except Exception as e:
            logger.error(f"send_inline_keyboard error: {e}")
            return {"error": str(e)}

# Основные функции для использования
async def send_news_with_importance(item: Dict):
    """Отправка новости с расчетом важности"""
    bot = NewsBot(BOT_TOKEN, USER_ID)
    await bot.send_news(item)

async def send_digest_news(news_list: List[Dict]):
    """Отправка дайджеста"""
    bot = NewsBot(BOT_TOKEN, USER_ID)
    await bot.send_digest(news_list)

async def get_stats():
    """Получение статистики"""
    bot = NewsBot(BOT_TOKEN, USER_ID)
    await bot.send_statistics()

async def show_menu():
    """Показать меню"""
    bot = NewsBot(BOT_TOKEN, USER_ID)
    await bot.interactive_menu()

# Пример использования с вашим парсером
async def process_and_send_news(news_items: List[Dict]):
    """Обработка и отправка новостей"""
    bot = NewsBot(BOT_TOKEN, USER_ID)
    
    for item in news_items:
        await bot.send_news(item, importance_threshold=0.6)  # Отправлять только важные новости
    
    # Отправляем дайджест
    await bot.send_digest(news_items[:5], "📰 Топ-5 важных новостей")

# Функция для обратной связи (можно вызывать из веб-интерфейса)
async def handle_feedback(url: str, feedback: str):
    """Обработка обратной связи пользователя"""
    db.save_feedback(url, feedback)
    logger.info(f"Feedback received for {url}: {feedback}")

# Тестирование
async def test_bot():
    """Тестовая отправка"""
    bot = NewsBot(BOT_TOKEN, USER_ID)
    await bot.send_text("🤖 Бот запущен и готов к работе!")
    await bot.send_statistics()

if __name__ == "__main__":
    # Запуск теста
    asyncio.run(test_bot())
    print("Бот готов к работе!")
