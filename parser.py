import re
import httpx
from bs4 import BeautifulSoup
import feedparser

STOPWORDS = set("the a an and or to of in for on with is that this from by as at it be was were are its their you your we our they he she и или но не на в для с по что это как его её их они мы вы он она оно то все эти тот та те".split())

def extract_words(text):
    words = re.findall(r"[a-zA-Zа-яА-Я]+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]

async def fetch_hn():
    items = []
    async with httpx.AsyncClient(timeout=15) as c:
        ids = (await c.get("https://hacker-news.firebaseio.com/v0/topstories.json")).json()[:15]
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
                    "words": extract_words(title),
                    "category": "programming"
                })
            except Exception:
                continue
    return items

async def fetch_habr():
    items = []
    try:
        feed = feedparser.parse("https://habr.com/ru/rss/all/?fl=ru")
        for entry in feed.entries[:20]:
            title = entry.get("title","")
            summary = entry.get("summary","")
            if len(summary) > 200:
                summary = summary[:200] + "..."
            items.append({
                "id": f"habr_{entry.get('id','')}",
                "title": title,
                "url": entry.get("link",""),
                "source": "Хабр",
                "summary": summary,
                "words": extract_words(title + " " + summary),
                "category": "programming"
            })
    except Exception:
        pass
    return items

async def fetch_devto():
    items = []
    async with httpx.AsyncClient(timeout=15) as c:
        try:
            r = await c.get("https://dev.to/api/articles?top=7&per_page=15")
            for a in r.json():
                title = a.get("title","")
                desc = a.get("description","")
                items.append({
                    "id": f"devto_{a['id']}",
                    "title": title,
                    "url": a.get("url"),
                    "source": "Dev.to",
                    "summary": desc,
                    "words": extract_words(title + " " + desc + " " + " ".join(a.get("tag_list",[]))),
                    "category": "programming"
                })
        except Exception:
            pass
    return items

async def fetch_github_trending():
    items = []
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent":"Mozilla/5.0"}) as c:
        try:
            r = await c.get("https://github.com/trending")
            soup = BeautifulSoup(r.text, "html.parser")
            for repo in soup.select("article.Box-row")[:12]:
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
                    "words": extract_words(name + " " + desc_text),
                    "category": "projects"
                })
        except Exception:
            pass
    return items

async def fetch_art():
    items = []
    rss_feeds = [
        ("https://www.colossal.org/feed/", "Colossal"),
        ("https://www.itsnicethat.com/feed/atom", "It's Nice That"),
        ("https://www.dezeen.com/rss/", "Dezeen"),
    ]
    for feed_url, source in rss_feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:8]:
                title = entry.get("title","")
                summary = entry.get("summary","")
                if len(summary) > 180:
                    summary = summary[:180] + "..."
                items.append({
                    "id": f"art_{source}_{entry.get('id','')}",
                    "title": title,
                    "url": entry.get("link",""),
                    "source": source,
                    "summary": summary,
                    "words": extract_words(title + " " + summary),
                    "category": "art"
                })
        except Exception:
            continue
    return items

async def fetch_all():
    results = await asyncio.gather(
        fetch_hn(), fetch_habr(), fetch_devto(), 
        fetch_github_trending(), fetch_art(),
        return_exceptions=True
    )
    items = []
    for r in results:
        if isinstance(r, list):
            items.extend(r)
    return items

import asyncio
