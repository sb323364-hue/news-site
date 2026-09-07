import re
import httpx
import feedparser
import asyncio
import random

STOPWORDS = set("the a an and or to of in for on with is that this from by as at it be was were are its their you your we our they he she и или но не на в для с по что это как его её их они мы вы он она оно то все эти тот та те".split())

UNSPLASH_KEY = "3M6g8CnURKe2FDLohVFX-qL9WxZq-xmpCSLXEebzYU8"
PEXELS_KEY = "E3y39aPY2n66afqFL5ceGwDF5HAAzO5bFy5qpt9Kvjpfi4f4PlxcBziY"

# Вайбовые запросы в стиле 2017: природа, ностальгия, film photography, aesthetic
SEARCH_TERMS = [
    "nature aesthetic",
    "vintage photography", 
    "film photography nature",
    "moody landscape",
    "forest aesthetic",
    "nostalgic vibes",
    "grainy film",
    "pastel nature",
    "dreamy landscape",
    "cottagecore",
    "misty forest",
    "ocean aesthetic"
]

def extract_words(text):
    words = re.findall(r"[a-zA-Zа-яА-Я]+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]

async def fetch_unsplash():
    items = []
    async with httpx.AsyncClient(timeout=15) as c:
        try:
            term = random.choice(SEARCH_TERMS)
            r = await c.get(
                f"https://api.unsplash.com/photos/random",
                params={"count": 20, "query": term},
                headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"}
            )
            if r.status_code == 200:
                for photo in r.json():
                    title = photo.get("description") or photo.get("alt_description") or "Untitled"
                    items.append({
                        "id": f"unsplash_{photo['id']}",
                        "title": title,
                        "url": photo["links"]["html"],
                        "source": "Unsplash",
                        "summary": "",
                        "image_url": photo["urls"]["regular"],
                        "words": extract_words(title),
                        "category": "vibes"
                    })
        except Exception as e:
            print(f"Unsplash error: {e}")
    return items

async def fetch_pexels():
    items = []
    async with httpx.AsyncClient(timeout=15) as c:
        try:
            term = random.choice(SEARCH_TERMS)
            r = await c.get(
                f"https://api.pexels.com/v1/search",
                params={"query": term, "per_page": 20},
                headers={"Authorization": PEXELS_KEY}
            )
            if r.status_code == 200:
                for photo in r.json().get("photos", []):
                    items.append({
                        "id": f"pexels_{photo['id']}",
                        "title": photo.get("alt") or "Untitled",
                        "url": photo["url"],
                        "source": "Pexels",
                        "summary": "",
                        "image_url": photo["src"]["large"],
                        "words": extract_words(photo.get("alt", "")),
                        "category": "vibes"
                    })
        except Exception as e:
            print(f"Pexels error: {e}")
    return items

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
