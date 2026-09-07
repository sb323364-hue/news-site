from apscheduler.schedulers.asyncio import AsyncIOScheduler
from parser import fetch_all
from database import save_news
from telegram import notify_if_important

scheduler = AsyncIOScheduler()

async def job():
    items = await fetch_all()
    save_news(items)
    for it in items:
        await notify_if_important(it)

def start():
    scheduler.add_job(job, "interval", minutes=30, next_run_time=None)
    scheduler.start()
