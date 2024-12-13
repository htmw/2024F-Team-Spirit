from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pydantic import BaseModel
import httpx
import requests
import os
import asyncio
from datetime import datetime
from cachetools import TTLCache
from dotenv import load_dotenv

load_dotenv()

class NewsArticle(BaseModel):
    id: str
    title: str
    description: str
    source: str
    url: str
    publishedAt: datetime
    relatedSymbols: List[str]
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None

app = FastAPI(title="News Sentiment API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

news_cache = TTLCache(maxsize=500, ttl=600)
rate_limit_cache = TTLCache(maxsize=100, ttl=10)

MARKETAUX_API = {
    "base_url": "https://api.marketaux.com/v1",
    "token": os.getenv("MARKETAUX_API_TOKEN")
}

HUGGINGFACE_API = {
    "url": "https://api-inference.huggingface.co/models/mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis",
    "token": os.getenv("HUGGINGFACE_API_TOKEN")
}

async def get_sentiment(text: str) -> tuple[str, float]:
    try:
        response = requests.post(
            HUGGINGFACE_API["url"],
            headers={"Authorization": f"Bearer {HUGGINGFACE_API['token']}"},
            json={"inputs": text}
        )
        result = response.json()
        sentiment = max(result[0], key=lambda x: x['score'])
        sentiment_mapping = {
            "positive": "POSITIVE",
            "neutral": "NEUTRAL",
            "negative": "NEGATIVE"
        }
        return sentiment_mapping.get(sentiment['label'].lower(), "NEUTRAL"), sentiment['score']
    except Exception:
        return "NEUTRAL", 0.5

def transform_news_data(marketaux_response):
    transformed_news = []
    for article in marketaux_response["data"]:
        related_symbols = [
            entity["symbol"]
            for entity in article["entities"]
            if entity["type"] == "equity"
        ]
        transformed_news.append({
            "id": article["uuid"],
            "title": article["title"],
            "description": article["description"] or article["snippet"],
            "source": article["source"],
            "url": article["url"],
            "publishedAt": article["published_at"],
            "relatedSymbols": related_symbols
        })
    return transformed_news

async def fetch_news_page(client, symbols: Optional[str], page: int, limit: int):
    try:
        params = {
            "api_token": MARKETAUX_API["token"],
            "symbols": symbols or "",
            "filter_entities": "true",
            "language": "en",
            "page": page,
            "limit": limit
        }
        response = await client.get(f"{MARKETAUX_API['base_url']}/news/all", params=params)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None

async def fetch_all_news_pages(symbols: Optional[str], base_limit: int = 10):
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [
            fetch_news_page(client, symbols, page, base_limit)
            for page in range(1, 4)
        ]
        results = await asyncio.gather(*tasks)

        all_news = []
        for result in results:
            if result and 'data' in result:
                news_data = transform_news_data(result)
                for article in news_data:
                    text_for_sentiment = f"{article['title']}. {article['description']}"
                    sentiment_label, sentiment_score = await get_sentiment(text_for_sentiment)
                    article["sentiment"] = sentiment_label
                    article["sentiment_score"] = sentiment_score
                all_news.extend(news_data)

        return all_news

@app.get("/")
async def root():
    return {
        "message": "Welcome to News Sentiment API",
        "version": "2.0",
        "features": ["Multi-page fetching", "Sentiment analysis", "Rate limiting"]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(news_cache)
    }

@app.get("/api/news")
async def get_news(symbols: Optional[str] = None, page: int = 1, limit: int = 30):
    try:
        rate_limit_key = f"rate_limit:{symbols or 'general'}"
        if rate_limit_key in rate_limit_cache:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait 10 seconds between requests."
            )

        rate_limit_cache[rate_limit_key] = datetime.now()
        cache_key = f"news:{symbols}:{page}:{limit}"

        if cache_key in news_cache:
            return news_cache[cache_key]

        news_data = await fetch_all_news_pages(symbols, limit // 3)

        if news_data:
            news_data.sort(key=lambda x: x["publishedAt"], reverse=True)
            news_cache[cache_key] = news_data
            return news_data

        return []

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/news/refresh")
async def refresh_news(symbols: Optional[str] = None):
    try:
        rate_limit_key = f"rate_limit_refresh:{symbols or 'general'}"
        if rate_limit_key in rate_limit_cache:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait 10 seconds between refreshes."
            )

        rate_limit_cache[rate_limit_key] = datetime.now()
        news_data = await fetch_all_news_pages(symbols, 10)

        if news_data:
            news_data.sort(key=lambda x: x["publishedAt"], reverse=True)
            cache_key = f"news:{symbols}:1:30"
            news_cache[cache_key] = news_data
            return news_data

        return []

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats(symbols: Optional[str] = None):
    try:
        cache_key = f"news:{symbols}:1:30"
        if cache_key not in news_cache:
            return {
                "status": "no_data",
                "message": "No data available. Make a news request first."
            }

        news_data = news_cache[cache_key]
        sentiment_counts = {"POSITIVE": 0, "NEUTRAL": 0, "NEGATIVE": 0}
        source_counts = {}
        symbol_counts = {}
        total_articles = len(news_data)

        for article in news_data:
            sentiment_counts[article["sentiment"]] += 1
            source_counts[article["source"]] = source_counts.get(article["source"], 0) + 1
            for symbol in article["relatedSymbols"]:
                symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1

        return {
            "total_articles": total_articles,
            "sentiment_distribution": sentiment_counts,
            "top_sources": dict(sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:5]),
            "top_symbols": dict(sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:5])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 3000)), reload=True)
