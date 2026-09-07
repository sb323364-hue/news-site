import re
import httpx
import asyncio
import random

STOPWORDS = set("the a an and or to of in for on with is that this from by as at it be was were are its their you your we our they he she и или но не на в для с по что это как его её их они мы вы он она оно то все эти тот та те".split())

UNSPLASH_KEY = "3M6g8CnURKe2FDLohVFX-qL9WxZq-xmpCSLXEebzYU8"
PEXELS_KEY = "E3y39aPY2n66afqFL5ceGwDF5HAAzO5bFy5qpt9Kvjpfi4f4PlxcBziY"

# Закаты — отдельная группа, всегда попадёт в подборку
SUNSET_TERMS = [
    "sunset",
    "sunset aesthetic",
    "golden hour",
    "sunrise",
    "dusk sky",
    "pink sunset",
    "sunset clouds",
    "sunset ocean",
    "orange sky",
    "sunset silhouette"
]

# Вайбовые — природа, ностальгия, 2017 aesthetic
VIBE_TERMS = [
    "nature aesthetic",
    "film photography nature",
    "moody landscape",
    "forest aesthetic",
    "misty forest",
    "ocean aesthetic",
    "dreamy landscape",
    "pastel nature",
    "grainy film",
    "nostalgic vibes",
    "vintage photography",
    "cottagecore"
]

def extract_words(text):
    words = re.findall(r"[a-zA-Zа-яА-Я]+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]

async def fetch_unsplash_query(c, term, source_tag):
    items = []
    try:
        r = await c.get(
            "https://api.unsplash.com/photos/random",
            params={"count": 15, "query": term},
            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"}
        )
        if r.status_code == 200:
            for photo in r.json():
                title = photo.get("description") or photo.get("alt_description") or term.title()
                items.append({
                    "id": f"unsplash_{photo['id']}",
                    "title": title,
                    "url": photo["links"]["html"],
                    "source": "Unsplash",
                    "summary": "",
                    "image_url": photo["urls"]["regular"],
                    "words": extract_words(title + " " + term),
                    "category": source_tag
                })
    except Exception as e:
        print(f"Unsplash {term} error: {e}")
    return items

async def fetch_pexels_query(c, term, source_tag):
    items = []
    try:
        r = await c.get(
            "https://api.pexels.com/v1/search",
            params={"query": term, "per_page": 15},
            headers={"Authorization": PEXELS_KEY}
        )
        if r.status_code == 200:
            for photo in r.json().get("photos", []):
                title = photo.get("alt") or term.title()
                items.append({
                    "id": f"pexels_{photo['id']}",
                    "title": title,
                    "url": photo["url"],
                    "source": "Pexels",
                    "summary": "",
                    "image_url": photo["src"]["large"],
                    "words": extract_words(title + " " + term),
                    "category": source_tag
                })
    except Exception as e:
        print(f"Pexels {term} error: {e}")
    return items

async def fetch_unsplash():
    # Берём 2 случайных запроса: 1 закат + 1 вайб
    sunset = random.choice(SUNSET_TERMS)
    vibe = random.choice(VIBE_TERMS)
    
    async with httpx.AsyncClient(timeout=15) as c:
        sunset_items = await fetch_unsplash_query(c, sunset, "sunset")
        vibe_items = await fetch_unsplash_query(c, vibe, "vibes")
    return sunset_items + vibe_items

async def fetch_pexels():
    sunset = random.choice(SUNSET_TERMS)
    vibe = random.choice(VIBE_TERMS)
    
    async with httpx.AsyncClient(timeout=15) as c:
        sunset_items = await fetch_pexels_query(c, sunset, "sunset")
        vibe_items = await fetch_pexels_query(c, vibe, "vibes")
    return sunset_items + vibe_items

async def fetch_all():
    results = await asyncio.gather(
        fetch_unsplash(), fetch_pexels(),
        return_exceptions=True
    )
    items = []
    for r in results:
        if isinstance(r, list):
            items.extend(r)
    return items
