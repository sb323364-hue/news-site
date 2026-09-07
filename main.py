from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import init_db, get_news, set_rating, get_conn
from scheduler import start, job
import os

app = FastAPI()
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup():
    init_db()
    start()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "news": get_news()})

@app.post("/rate/{news_id}/{rating}")
async def rate(news_id: str, rating: int):
    set_rating(news_id, rating)
    return RedirectResponse("/", status_code=303)

@app.get("/debug")
async def debug():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) as c FROM news").fetchone()["c"]
    with_images = conn.execute("SELECT COUNT(*) as c FROM news WHERE image_url != ''").fetchone()["c"]
    sample = conn.execute("SELECT id, title, image_url, source FROM news LIMIT 3").fetchall()
    conn.close()
    return {
        "total_news": total,
        "with_images": with_images,
        "sample": [dict(r) for r in sample]
    }

@app.get("/send-test")
async def send_test():
    from telegram import send_photo
    from database import get_conn
    
    conn = get_conn()
    row = conn.execute("SELECT title, url, source, image_url FROM news WHERE image_url != '' LIMIT 1").fetchone()
    conn.close()
    
    if not row:
        return {"error": "No news with image_url in DB. Run /run-job first."}
    
    item = dict(row)
    caption = f"✨ TEST: {item['title']}\n{item['url']}\n— {item['source']}"
    result = await send_photo(item["image_url"], caption)
    return {"item": item, "result": result}

@app.get("/run-job")
async def run_job():
    await job()
    return {"status": "done"}

@app.get("/test-text")
async def test_text():
    from telegram import send_text
    result = await send_text("🔧 Текстовый тест. Если видишь — бот работает.")
    return {"result": result}
