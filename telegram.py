import httpx
from database import predict_importance, count_ratings
import traceback

BOT_TOKEN = "8725608346:AAGZ8ddO1H5ul-DkOugsGnrgucel0tGrNRw"
USER_ID = "1400906997"
THRESHOLD = 0.3

async def send_photo(image_url, caption):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                json={
                    "chat_id": USER_ID,
                    "photo": image_url,
                    "caption": caption,
                    "disable_web_page_preview": True
                }
            )
            return r.json()
    except Exception as e:
        print("Telegram send_photo error:", e)
        return None

async def send_text(text):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": USER_ID, "text": text, "disable_web_page_preview": True}
            )
            return r.json()
    except Exception as e:
        print("Telegram send_text error:", e)
        return None

async def notify_if_important(item):
    if count_ratings() < 30:
        return
    score = predict_importance(item.get("words", []))
    if score >= THRESHOLD:
        caption = f"🔥 {item['title']}\n{item['url']}\n— {item['source']}"
        if item.get("image_url"):
            await send_photo(item["image_url"], caption)
        else:
            await send_text(caption)
