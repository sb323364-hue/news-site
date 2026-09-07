from apscheduler.schedulers.asyncio import AsyncIOScheduler
from parser import fetch_all
from database import save_news, predict_importance
from telegram import notify_if_important
import asyncio

scheduler = AsyncIOScheduler()

async def job():
    try:
        items = await fetch_all()
        save_news(items)
        
        # Сортируем по важности и берём топ-5
        scored_items = []
        for item in items:
            score = predict_importance(item.get("words", []))
            scored_items.append((score, item))
        
        scored_items.sort(key=lambda x: x[0], reverse=True)
        top_items = [item for score, item in scored_items[:5]]
        
        # Отправляем только топ-5
        for it in top_items:
            await notify_if_important(it)
            
    except Exception as e:
        print(f"Job error: {e}")

def start():
    scheduler.add_job(job, "interval", minutes=30)
    scheduler.start()
    asyncio.create_task(job())
