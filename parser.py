import re
import httpx
from bs4 import BeautifulSoup
from collections import Counter

STOPWORDS = set("the a an and or to of in for on with is that this from by as at it be was were are its their you your we our they he she".split())

def extract_words(text):
    words = re.findall(r"[a-zA-Zа-яА-Я]+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]

async def fetch_hn():
    items = []
    async with httpx.AsyncClient(timeout=15) as c:
        ids = (await c.get("https://hacker-news.firebaseio.com/v0/topstories.json")).json()[:20]
        for i in ids:
            try:
                d = (await c.get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json")).json()
                if not d or d.get("type") != "story":
                    continue
                title = d.get("title","")
                items.append({
                    "id": f"hn_{i}",
                    "title": title,
                    "url": d.get("url") or f"https://news.ycombinator.com/item?id={i}",
                    "source": "Hacker News",
                    "summary": "",
                    "words": extract_words(title)
                })
            except Exception:
                continue
    return items

async def fetch_devto():
    items = []
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get("https://dev.to/api/articles?top=7&per_page=20")
        for a in r.json():
            title = a.get("title","")
            desc = a.get("description","")
            items.append({
                "id": f"devto_{a['id']}",
                "title": title,
                "url": a.get("url"),
                "source": "Dev.to",
                "summary": desc,
                "words": extract_words(title + " " + desc + " " + " ".join(a.get("tag_list",[])))
            })
    return items

async def fetch_github_trending():
    items = []
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent":"Mozilla/5.0"}) as c:
        r = await c.get("https://github.com/trending")
        soup = BeautifulSoup(r.text, "html.parser")
        for repo in soup.select("article.Box-row")[:15]:
            h1 = repo.select_one("h2 a")
            if not h1:
                continue
            name = h1.get_text(" ", strip=True).replace(" / ", "/")
            desc = repo.select_one("p")
            desc_text = desc.get_text(strip=True) if desc else ""
            url = "https://github.com" + h1.get("href","")
            items.append({
                "id": f"gh_{name.replace('/','_')}",
                "title": name,
                "url": url,
                "source": "GitHub Trending",
                "summary": desc_text,
                "words": extract_words(name + " " + desc_text)
            })
    return items

async def fetch_all():
    hn, devto, gh = await fetch_hn(), await fetch_devto(), await fetch_github_trending()
    return hn + devto + gh
