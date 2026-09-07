from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import init_db, get_news, set_rating
from scheduler import start
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

@app.get("/test-telegram")
async def test_telegram():
    from telegram import send
    result = await send("Тестовое сообщение. Если ты это видишь — бот работает!")
    return {"result": result}
