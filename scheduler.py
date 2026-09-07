from apscheduler.schedulers.asyncio import AsyncIOScheduler
from parser import fetch_all
from database import save_news
from telegram import notify_if_important
import asyncio

scheduler = AsyncIOScheduler()

async def job():
    try:
        items = await fetch_all()
        save_news(items)
        for it in items:
            await notify_if_important(it)
    except Exception as e:
        print(f"Job error: {e}")

def start():
    scheduler.add_job(job, "interval", minutes=30)
    scheduler.start()
    # Запускаем первый сбор сразу
    asyncio.create_task(job())
