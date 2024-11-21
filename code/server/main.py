from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pydantic import BaseModel
import httpx
import requests
import os
from datetime import datetime, timedelta
from cachetools import TTLCache
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import DESCENDING
from bson import ObjectId

load_dotenv()

app = FastAPI(title="News Sentiment API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGODB_URL)
db = client.news_sentiment_db
news_collection = db.news_articles

# Cache Configuration
news_cache = TTLCache(maxsize=100, ttl=300)

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

async def get_sentiment(text: str) -> str:
    try:
        response = requests.post(
            HUGGINGFACE_API["url"],
            headers={"Authorization": f"Bearer {HUGGINGFACE_API['token']}"},
            json={"inputs": text}
        )
        result = response.json()
        sentiment_mapping = {
            "positive": "POSITIVE",
            "neutral": "NEUTRAL",
            "negative": "NEGATIVE"
        }
        sentiment = max(result[0], key=lambda x: x['score'])
        return sentiment_mapping.get(sentiment['label'].lower(), "NEUTRAL")
    except Exception as e:
        print(f"Sentiment analysis error: {e}")
        return "NEUTRAL"

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
            "relatedSymbols": related_symbols,
            "created_at": datetime.utcnow()
        })
    return transformed_news

async def store_news_in_db(news_data: List[dict]):
    """Store news articles in MongoDB"""
    if not news_data:
        return

    # Convert datetime objects to string format for MongoDB
    for article in news_data:
        if isinstance(article["publishedAt"], str):
            article["publishedAt"] = datetime.fromisoformat(article["publishedAt"].replace('Z', '+00:00'))

    # Use bulk write operations for better performance
    try:
        operations = [
            {
                "updateOne": {
                    "filter": {"id": article["id"]},
                    "update": {"$set": article},
                    "upsert": True
                }
            }
            for article in news_data
        ]
        await news_collection.bulk_write(operations)
    except Exception as e:
        print(f"Error storing news in MongoDB: {e}")

async def get_news_from_db(symbols: Optional[List[str]] = None, limit: int = 10) -> List[dict]:
    """Retrieve news articles from MongoDB"""
    query = {}
    if symbols:
        query["relatedSymbols"] = {"$in": symbols}

    # Get articles from the last 24 hours
    time_threshold = datetime.utcnow() - timedelta(hours=24)
    query["created_at"] = {"$gte": time_threshold}

    cursor = news_collection.find(query)
    cursor.sort("publishedAt", DESCENDING).limit(limit)

    return await cursor.to_list(length=limit)

@app.get("/")
async def root():
    return {"message": "Welcome to News Sentiment API"}

@app.get("/health")
async def health_check():
    try:
        # Check MongoDB connection
        await client.admin.command('ping')
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "mongodb_status": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "mongodb_status": "disconnected",
            "error": str(e)
        }

@app.get("/api/news")
async def get_news(symbols: Optional[str] = None, page: int = 1, limit: int = 10):
    try:
        # Parse symbols
        symbol_list = symbols.split(',') if symbols else None

        # Check cache first
        cache_key = f"news:{symbols}:{page}:{limit}"
        if cache_key in news_cache:
            return news_cache[cache_key]

        # Check MongoDB for recent articles
        db_news = await get_news_from_db(symbol_list, limit)
        if db_news:
            news_cache[cache_key] = db_news
            return db_news

        # If no recent articles in MongoDB, fetch from MarketAux
        async with httpx.AsyncClient(timeout=30.0) as client:
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

            news_data = transform_news_data(response.json())
            for article in news_data:
                text_for_sentiment = f"{article['title']}. {article['description']}"
                article["sentiment"] = await get_sentiment(text_for_sentiment)

            # Store in MongoDB and cache
            await store_news_in_db(news_data)
            news_cache[cache_key] = news_data
            return news_data

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/news/refresh")
async def refresh_news(symbols: Optional[str] = None):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "api_token": MARKETAUX_API["token"],
                "symbols": symbols or "",
                "filter_entities": "true",
                "language": "en",
                "limit": 10
            }
            response = await client.get(f"{MARKETAUX_API['base_url']}/news/all", params=params)
            response.raise_for_status()

            news_data = transform_news_data(response.json())
            for article in news_data:
                text_for_sentiment = f"{article['title']}. {article['description']}"
                article["sentiment"] = await get_sentiment(text_for_sentiment)

            # Store in MongoDB
            await store_news_in_db(news_data)
            return news_data

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 3000)), reload=True)
