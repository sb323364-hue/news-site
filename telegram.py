import httpx
from database import predict_importance, count_ratings

BOT_TOKEN = "8725608346:AAGZ8ddO1H5ul-DkOugsGnrgucel0tGrNRw"
USER_ID = "1400906997"
THRESHOLD = 0.3

async def send_photo(image_url, caption):
    try:
        if not image_url:
            return await send_text(caption)
        
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
            if r.status_code != 200:
                print("Photo failed, sending text instead")
                return await send_text(caption)
            return r.json()
    except Exception as e:
        print(f"Telegram send_photo error: {e}")
        return await send_text(caption)

async def send_text(text):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": USER_ID, "text": text, "disable_web_page_preview": True}
            )
            return r.json()
    except Exception as e:
        print(f"Telegram send_text error: {e}")
        return None

async def notify_if_important(item):
    try:
        if count_ratings() < 30:
            return
        score = predict_importance(item.get("words", []))
        if score >= THRESHOLD:
            caption = f"✨ {item['title']}\n{item['url']}\n— {item['source']}"
            image_url = item.get("image_url", "")
            await send_photo(image_url, caption)
    except Exception as e:
        print(f"Notify error: {e}")
