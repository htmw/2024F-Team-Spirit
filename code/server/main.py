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

app = FastAPI(title="News Sentiment API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Increase cache size and TTL for better performance
news_cache = TTLCache(maxsize=500, ttl=600)  # 10 minutes cache
rate_limit_cache = TTLCache(maxsize=100, ttl=10)  # 10 seconds rate limit

MARKETAUX_API = {
    "base_url": "https://api.marketaux.com/v1",
    "token": os.getenv("MARKETAUX_API_TOKEN", "b4sLrUAkKochUZHyHWT3PksORZeFsZ5LE3Ouw3hy")
}

HUGGINGFACE_API = {
    "url": "https://api-inference.huggingface.co/models/mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis",
    "token": os.getenv("HUGGINGFACE_API_TOKEN", "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")
}

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

async def get_sentiment(text: str) -> tuple[str, float]:
    """Get sentiment analysis with confidence score"""
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
    except Exception as e:
        print(f"Sentiment analysis error: {e}")
        return "NEUTRAL", 0.5

def transform_news_data(marketaux_response):
    """Transform API response to news articles"""
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
    """Fetch a single page of news from MarketAux API"""
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
    except Exception as e:
        print(f"Error fetching page {page}: {e}")
        return None

async def fetch_all_news_pages(symbols: Optional[str], base_limit: int = 10):
    """Fetch multiple pages of news concurrently"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create tasks for fetching three pages
        tasks = [
            fetch_news_page(client, symbols, page, base_limit)
            for page in range(1, 4)  # Pages 1, 2, and 3
        ]

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)

        # Merge and process results
        all_news = []
        for result in results:
            if result and 'data' in result:
                news_data = transform_news_data(result)
                # Get sentiment for each article
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
        # Check rate limiting
        rate_limit_key = f"rate_limit:{symbols or 'general'}"
        if rate_limit_key in rate_limit_cache:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait 10 seconds between requests."
            )

        # Set rate limit
        rate_limit_cache[rate_limit_key] = datetime.now()

        # Check cache
        cache_key = f"news:{symbols}:{page}:{limit}"
        if cache_key in news_cache:
            return news_cache[cache_key]

        # Fetch news from all three pages
        news_data = await fetch_all_news_pages(symbols, limit // 3)

        if news_data:
            # Sort by publishedAt date
            news_data.sort(key=lambda x: x["publishedAt"], reverse=True)

            # Store in cache
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
        # Check rate limiting
        rate_limit_key = f"rate_limit_refresh:{symbols or 'general'}"
        if rate_limit_key in rate_limit_cache:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait 10 seconds between refreshes."
            )

        # Set rate limit
        rate_limit_cache[rate_limit_key] = datetime.now()

        # Fetch fresh news from all three pages
        news_data = await fetch_all_news_pages(symbols, 10)

        if news_data:
            # Sort by publishedAt date
            news_data.sort(key=lambda x: x["publishedAt"], reverse=True)

            # Update cache with new data
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
    """Get statistics about the news data"""
    try:
        cache_key = f"news:{symbols}:1:30"
        if cache_key not in news_cache:
            return {
                "status": "no_data",
                "message": "No data available. Make a news request first."
            }

        news_data = news_cache[cache_key]

        # Calculate statistics
        sentiment_counts = {"POSITIVE": 0, "NEUTRAL": 0, "NEGATIVE": 0}
        source_counts = {}
        symbol_counts = {}
        total_articles = len(news_data)

        for article in news_data:
            # Count sentiments
            sentiment_counts[article["sentiment"]] += 1

            # Count sources
            source_counts[article["source"]] = source_counts.get(article["source"], 0) + 1

            # Count symbols
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
