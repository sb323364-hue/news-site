import re
import httpx
from bs4 import BeautifulSoup
import feedparser
import asyncio
import random

STOPWORDS = set("the a an and or to of in for on with is that this from by as at it be was were are its their you your we our they he she и или но не на в для с по что это как его её их они мы вы он она оно то все эти тот та те".split())

UNSPLASH_KEY = "3M6g8CnURKe2FDLohVFX-qL9WxZq-xmpCSLXEebzYU8"
PEXELS_KEY = "E3y39aPY2n66afqFL5ceGwDF5HAAzO5bFy5qpt9Kvjpfi4f4PlxcBziY"

SEARCH_TERMS = ["design", "photography", "art", "illustration", "creative", "portrait", "landscape"]

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
                        "words": extract_words(title + " " + " ".join(photo.get("tags", [])[:5])),
                        "category": "photography"
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
                        "category": "photography"
                    })
        except Exception as e:
            print(f"Pexels error: {e}")
    return items

async def fetch_colossal():
    items = []
    try:
        feed = feedparser.parse("https://www.colossal.org/feed/")
        for entry in feed.entries[:15]:
            title = entry.get("title","")
            summary = entry.get("summary","")
            if len(summary) > 200:
                summary = summary[:200] + "..."
            
            # Извлекаем первую картинку из HTML
            image_url = ""
            if "content" in entry:
                soup = BeautifulSoup(entry.content[0].value, "html.parser")
                img = soup.find("img")
                if img and img.get("src"):
                    image_url = img["src"]
            
            items.append({
                "id": f"colossal_{entry.get('id','')}",
                "title": title,
                "url": entry.get("link",""),
                "source": "Colossal",
                "summary": summary,
                "image_url": image_url,
                "words": extract_words(title + " " + summary),
                "category": "art"
            })
    except Exception as e:
        print(f"Colossal error: {e}")
    return items

async def fetch_itsnicethat():
    items = []
    try:
        feed = feedparser.parse("https://www.itsnicethat.com/feed/atom")
        for entry in feed.entries[:15]:
            title = entry.get("title","")
            summary = entry.get("summary","")
            if len(summary) > 200:
                summary = summary[:200] + "..."
            
            image_url = ""
            if "content" in entry:
                soup = BeautifulSoup(entry.content[0].value, "html.parser")
                img = soup.find("img")
                if img and img.get("src"):
                    image_url = img["src"]
            
            items.append({
                "id": f"int_{entry.get('id','')}",
                "title": title,
                "url": entry.get("link",""),
                "source": "It's Nice That",
                "summary": summary,
                "image_url": image_url,
                "words": extract_words(title + " " + summary),
                "category": "design"
            })
    except Exception as e:
        print(f"It's Nice That error: {e}")
    return items

async def fetch_awwwards():
    items = []
    try:
        feed = feedparser.parse("https://www.awwwards.com/blog/feed/")
        for entry in feed.entries[:12]:
            title = entry.get("title","")
            summary = entry.get("summary","")
            if len(summary) > 200:
                summary = summary[:200] + "..."
            
            image_url = ""
            if "content" in entry:
                soup = BeautifulSoup(entry.content[0].value, "html.parser")
                img = soup.find("img")
                if img and img.get("src"):
                    image_url = img["src"]
            
            items.append({
                "id": f"awwwards_{entry.get('id','')}",
                "title": title,
                "url": entry.get("link",""),
                "source": "Awwwards",
                "summary": summary,
                "image_url": image_url,
                "words": extract_words(title + " " + summary),
                "category": "design"
            })
    except Exception as e:
        print(f"Awwwards error: {e}")
    return items

async def fetch_dribbble():
    items = []
    try:
        feed = feedparser.parse("https://dribbble.com/shots/popular.rss")
        for entry in feed.entries[:15]:
            title = entry.get("title","")
            
            image_url = ""
            if "content" in entry:
                soup = BeautifulSoup(entry.content[0].value, "html.parser")
                img = soup.find("img")
                if img and img.get("src"):
                    image_url = img["src"]
            
            items.append({
                "id": f"dribbble_{entry.get('id','')}",
                "title": title,
                "url": entry.get("link",""),
                "source": "Dribbble",
                "summary": "",
                "image_url": image_url,
                "words": extract_words(title),
                "category": "design"
            })
    except Exception as e:
        print(f"Dribbble error: {e}")
    return items

async def fetch_all():
    results = await asyncio.gather(
        fetch_unsplash(), fetch_pexels(), fetch_colossal(),
        fetch_itsnicethat(), fetch_awwwards(), fetch_dribbble(),
        return_exceptions=True
    )
    items = []
    for r in results:
        if isinstance(r, list):
            items.extend(r)
    return items
