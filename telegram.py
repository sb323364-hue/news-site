import httpx
from database import predict_importance, count_ratings

BOT_TOKEN = "PUT_NEW_TOKEN_HERE"   # ← замени после revoke
USER_ID = "1400906997"
THRESHOLD = 0.5   # порог важности

async def send(text):
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": USER_ID, "text": text, "disable_web_page_preview": True}
        )

async def notify_if_important(item):
    # пока оценок мало — не спамим
    if count_ratings() < 30:
        return
    score = predict_importance(item.get("words", []))
    if score >= THRESHOLD:
        text = f"🔥 {item['title']}\n{item['url']}\n— {item['source']}"
        await send(text)
