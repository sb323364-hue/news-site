import httpx

BOT_TOKEN = "8725608346:AAGZ8ddO1H5ul-DkOugsGnrgucel0tGrNRw"
USER_ID = "1400906997"

async def send_photo(image_url, caption):
    result = {"photo": None, "text": None}
    
    # Пытаемся отправить фото
    if image_url:
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    json={
                        "chat_id": USER_ID,
                        "photo": image_url,
                        "caption": caption[:1000]
                    }
                )
                result["photo"] = {"status": r.status_code, "body": r.json()}
                if r.status_code == 200 and r.json().get("ok"):
                    return result
                print(f"sendPhoto failed: {r.status_code} {r.text}")
        except Exception as e:
            result["photo"] = {"error": str(e)}
            print(f"sendPhoto exception: {e}")
    
    # Фолбэк на текст
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": USER_ID, "text": caption}
            )
            result["text"] = {"status": r.status_code, "body": r.json()}
    except Exception as e:
        result["text"] = {"error": str(e)}
    
    return result

async def send_text(text):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": USER_ID, "text": text}
            )
            return r.json()
    except Exception as e:
        return {"error": str(e)}

async def notify_if_important(item):
    caption = f"✨ {item.get('title','')}\n{item.get('url','')}\n— {item.get('source','')}"
    image_url = item.get("image_url", "")
    await send_photo(image_url, caption)
