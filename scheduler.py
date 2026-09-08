from apscheduler.schedulers.asyncio import AsyncIOScheduler
from parser import fetch_all
from database import save_news, predict_importance
from telegram import notify_if_important, send_to_channel
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# ============================================
# ОСНОВНАЯ ЗАДАЧА (каждые 30 минут)
# ============================================
async def job():
    """Сбор новостей и отправка пользователям (каждые 30 минут)"""
    try:
        logger.info("📰 Starting news collection...")
        
        items = await fetch_all()
        logger.info(f"✅ Fetched {len(items)} news items")
        
        save_news(items)
        
        # Сортируем по важности и берём топ-5
        scored_items = []
        for item in items:
            score = predict_importance(item.get("words", []))
            scored_items.append((score, item))
        
        scored_items.sort(key=lambda x: x[0], reverse=True)
        top_items = [item for score, item in scored_items[:5]]
        
        # Отправляем топ-5 пользователям
        logger.info(f"📤 Sending {len(top_items)} important news to users")
        for it in top_items:
            await notify_if_important(it)
        
        logger.info("✅ News collection completed")
            
    except Exception as e:
        logger.error(f"❌ Job error: {e}")

# ============================================
# ЗАДАЧА ДЛЯ КАНАЛА (каждые 2 часа)
# ============================================
async def channel_job():
    """Отправка в канал (каждые 2 часа) - только с фото"""
    try:
        logger.info("📢 Starting channel job...")
        
        items = await fetch_all()
        
        if not items:
            logger.info("⏭️ No news items")
            return
        
        # Выбираем ТОЛЬКО те, у которых есть фото
        news_with_images = [item for item in items if item.get("image_url")]
        
        if not news_with_images:
            logger.info("⏭️ No news with images")
            return
        
        # Сортируем по важности
        scored_items = []
        for item in news_with_images:
            score = predict_importance(item.get("words", []))
            scored_items.append((score, item))
        
        scored_items.sort(key=lambda x: x[0], reverse=True)
        
        # Берем самую важную с фото
        best_item = scored_items[0][1]
        
        # Отправляем в канал
        await send_to_channel(best_item)
        logger.info(f"✅ Channel post sent: {best_item.get('title', '')[:30]}...")
        
    except Exception as e:
        logger.error(f"❌ Channel job error: {e}")

# ============================================
# ЗАПУСК ПЛАНИРОВЩИКА
# ============================================
def start():
    """Запуск планировщика"""
    # Каждые 30 минут - сбор и отправка пользователям
    scheduler.add_job(
        job, 
        "interval", 
        minutes=30,
        id='user_job',
        name='Отправка пользователям'
    )
    
    # Каждые 2 часа - отправка в канал
    scheduler.add_job(
        channel_job,
        "interval",
        hours=2,
        id='channel_job',
        name='Отправка в канал'
    )
    
    scheduler.start()
    logger.info("✅ Scheduler started:")
    logger.info("   📊 Users: every 30 minutes")
    logger.info("   📢 Channel: every 2 hours")
    
    # Первый запуск сразу
    asyncio.create_task(job())
    asyncio.create_task(channel_job())

# ============================================
# ФУНКЦИИ ДЛЯ РУЧНОГО ЗАПУСКА
# ============================================
async def run_job():
    """Ручной запуск сбора новостей"""
    await job()

async def run_channel_job():
    """Ручной запуск отправки в канал"""
    await channel_job()

def stop():
    """Остановка планировщика"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
