from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import init_db, get_news, set_rating, get_conn
from scheduler import start, job
from telegram import send_photo, send_text, notify_if_important
from datetime import datetime
import os
import logging
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="News Bot")

# Создаем директории
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Монтируем статику
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ============================================
# ЗАПУСК ПРИ СТАРТЕ
# ============================================
@app.on_event("startup")
async def startup():
    """Инициализация при старте"""
    logger.info("🚀 Application starting...")
    try:
        init_db()
        start()  # Запускаем планировщик
        logger.info("✅ Database and scheduler initialized")
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")

# ============================================
# ОСНОВНЫЕ ЭНДПОИНТЫ
# ============================================
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница"""
    try:
        news = get_news()
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "news": news,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        logger.error(f"Index error: {e}")
        # Если шаблоны не работают - показываем простую страницу
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>News Bot</title>
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; background: #f0f2f5; }
            .container { background: white; padding: 30px; border-radius: 10px; max-width: 400px; margin: 0 auto; }
            h1 { color: #1a1a2e; }
            .status { color: #4CAF50; }
        </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 News Bot</h1>
                <p class="status">✅ Бот работает</p>
                <p><a href="/run-job">🚀 Запустить сбор</a></p>
                <p><a href="/debug">🔍 Debug</a></p>
                <p><a href="/ping">🔄 Ping</a></p>
                <small>⏰ {}</small>
            </div>
        </body>
        </html>
        """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return HTMLResponse(content=html)

# ============================================
# ЭНДПОИНТЫ ДЛЯ PINGVIBES (минимальный ответ)
# ============================================
@app.get("/ping")
async def ping():
    """Для PingVibes - минимальный ответ (всего несколько байт)"""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "uptime": "running"
    }

@app.get("/healthz")
async def healthz():
    """Для PingVibes - максимально короткий ответ"""
    return "OK"

@app.get("/health")
async def health():
    """Проверка здоровья"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

# ============================================
# ОЦЕНКА НОВОСТЕЙ
# ============================================
@app.post("/rate/{news_id}/{rating}")
async def rate(news_id: str, rating: int):
    """Оценка новости"""
    try:
        set_rating(news_id, rating)
        return RedirectResponse("/", status_code=303)
    except Exception as e:
        logger.error(f"Rating error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# ============================================
# ДЕБАГ И ТЕСТЫ
# ============================================
@app.get("/debug")
async def debug():
    """Отладочная информация"""
    try:
        conn = get_conn()
        total = conn.execute("SELECT COUNT(*) as c FROM news").fetchone()["c"]
        with_images = conn.execute("SELECT COUNT(*) as c FROM news WHERE image_url != ''").fetchone()["c"]
        sample = conn.execute("SELECT id, title, image_url, source FROM news LIMIT 3").fetchall()
        conn.close()
        
        return {
            "total_news": total,
            "with_images": with_images,
            "sample": [dict(r) for r in sample],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/send-test")
async def send_test():
    """Тест отправки фото"""
    try:
        conn = get_conn()
        row = conn.execute(
            "SELECT title, url, source, image_url FROM news WHERE image_url != '' LIMIT 1"
        ).fetchone()
        conn.close()
        
        if not row:
            return {"error": "No news with image_url in DB. Run /run-job first."}
        
        item = dict(row)
        caption = f"✨ TEST: {item['title']}\n{item['url']}\n— {item['source']}"
        result = await send_photo(item["image_url"], caption)
        return {"item": item, "result": result}
    except Exception as e:
        return {"error": str(e)}

@app.get("/test-text")
async def test_text():
    """Тест отправки текста"""
    try:
        result = await send_text("🔧 Текстовый тест. Если видишь — бот работает.")
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}

# ============================================
# ЗАПУСК ПАРСЕРА
# ============================================
@app.get("/run-job")
async def run_job(background_tasks: BackgroundTasks):
    """Запуск парсера в фоне"""
    try:
        # Запускаем задачу в фоне
        background_tasks.add_task(job)
        return {
            "status": "started",
            "message": "Parsing started in background",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Run job error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# ============================================
# API ДЛЯ НОВОСТЕЙ (с ограничением)
# ============================================
@app.get("/api/news")
async def api_news(limit: int = 10):
    """API для получения новостей"""
    try:
        conn = get_conn()
        news = conn.execute(
            "SELECT id, title, url, source, date, rating, image_url FROM news ORDER BY date DESC LIMIT ?",
            (min(limit, 20),)  # Максимум 20
        ).fetchall()
        conn.close()
        
        # Ограничиваем размер данных
        result = []
        for item in news:
            result.append({
                "id": item["id"],
                "title": item["title"][:100],  # Ограничиваем длину
                "url": item["url"][:100],
                "source": item["source"],
                "date": str(item["date"])[:20],
                "rating": item["rating"],
                "has_image": bool(item["image_url"])
            })
        
        return JSONResponse({
            "count": len(result),
            "news": result
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ============================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# ============================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
