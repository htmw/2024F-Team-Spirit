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
import urllib.parse

load_dotenv()

app = FastAPI(title="News Sentiment Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Atlas Configuration
MONGODB_USERNAME = "spiritteam669"
MONGODB_PASSWORD = "eEmjqtLt4JYRryG3"
MONGODB_CLUSTER = "cluster0.ehf31.mongodb.net"
MONGODB_URL = f"mongodb+srv://{urllib.parse.quote_plus(MONGODB_USERNAME)}:{urllib.parse.quote_plus(MONGODB_PASSWORD)}@{MONGODB_CLUSTER}/?retryWrites=true&w=majority"

# Initialize MongoDB client
client = AsyncIOMotorClient(
    MONGODB_URL,
    retryWrites=True,
    w="majority",
    maxPoolSize=50,
    minPoolSize=10,
    maxIdleTimeMS=30000,
    tls=True,
    tlsAllowInvalidCertificates=True
)

# Initialize database and collections
db = client.news_sentiment_db
news_collection = db.news_articles
sentiment_collection = db.sentiments
content_collection = db.content

# Cache configuration
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

# Initialize indexes on startup
@app.on_event("startup")
async def create_indexes():
    try:
        # Create indexes for news_articles collection
        await news_collection.create_index([("id", DESCENDING)], unique=True)
        await news_collection.create_index([("publishedAt", DESCENDING)])
        await news_collection.create_index([("relatedSymbols", DESCENDING)])
        await news_collection.create_index([("created_at", DESCENDING)])

        # Create indexes for sentiment_collection
        await sentiment_collection.create_index([("article_id", DESCENDING)], unique=True)
        await sentiment_collection.create_index([("sentiment", DESCENDING)])

        # Create indexes for content_collection
        await content_collection.create_index([("article_id", DESCENDING)], unique=True)

        print("MongoDB indexes created successfully")
    except Exception as e:
        print(f"Error creating MongoDB indexes: {e}")

async def get_sentiment(text: str) -> dict:
    """Get sentiment analysis with score"""
    try:
        response = requests.post(
            HUGGINGFACE_API["url"],
            headers={"Authorization": f"Bearer {HUGGINGFACE_API['token']}"},
            json={"inputs": text}
        )
        result = response.json()
        sentiment = max(result[0], key=lambda x: x['score'])
        return {
            "label": sentiment['label'].upper(),
            "score": sentiment['score'],
            "analyzed_at": datetime.utcnow()
        }
    except Exception as e:
        print(f"Sentiment analysis error: {e}")
        return {
            "label": "NEUTRAL",
            "score": 0.5,
            "analyzed_at": datetime.utcnow()
        }

async def store_content(article_id: str, title: str, description: str):
    """Store article content in separate collection"""
    try:
        await content_collection.update_one(
            {"article_id": article_id},
            {
                "$set": {
                    "article_id": article_id,
                    "title": title,
                    "description": description,
                    "updated_at": datetime.utcnow()
                }
            },
            upsert=True
        )
    except Exception as e:
        print(f"Error storing content: {e}")
        raise

async def store_sentiment(article_id: str, sentiment_data: dict):
    """Store sentiment analysis in separate collection"""
    try:
        await sentiment_collection.update_one(
            {"article_id": article_id},
            {
                "$set": {
                    "article_id": article_id,
                    **sentiment_data
                }
            },
            upsert=True
        )
    except Exception as e:
        print(f"Error storing sentiment: {e}")
        raise

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
    """Store news articles with content and sentiment analysis"""
    if not news_data:
        return

    try:
        for article in news_data:
            # Handle datetime conversion
            if isinstance(article["publishedAt"], str):
                article["publishedAt"] = datetime.fromisoformat(article["publishedAt"].replace('Z', '+00:00'))

            # Store main article data
            await news_collection.update_one(
                {"id": article["id"]},
                {"$set": article},
                upsert=True
            )

            # Store content separately
            await store_content(
                article["id"],
                article["title"],
                article["description"]
            )

            # Perform and store sentiment analysis
            text_for_sentiment = f"{article['title']}. {article['description']}"
            sentiment_data = await get_sentiment(text_for_sentiment)
            await store_sentiment(article["id"], sentiment_data)

            # Update article with sentiment label
            article["sentiment"] = sentiment_data["label"]

        return True
    except Exception as e:
        print(f"Error storing news in MongoDB: {e}")
        raise

async def get_news_from_db(symbols: Optional[List[str]] = None, limit: int = 10) -> List[dict]:
    """Retrieve news articles with content and sentiment"""
    try:
        # Build query
        query = {}
        if symbols:
            query["relatedSymbols"] = {"$in": symbols}

        # Get articles from the last 24 hours
        time_threshold = datetime.utcnow() - timedelta(hours=24)
        query["created_at"] = {"$gte": time_threshold}

        # Aggregate pipeline to join collections
        pipeline = [
            {"$match": query},
            # Join with content collection
            {
                "$lookup": {
                    "from": "content",
                    "localField": "id",
                    "foreignField": "article_id",
                    "as": "content"
                }
            },
            # Join with sentiment collection
            {
                "$lookup": {
                    "from": "sentiments",
                    "localField": "id",
                    "foreignField": "article_id",
                    "as": "sentiment_data"
                }
            },
            # Unwind arrays created by lookups
            {"$unwind": "$content"},
            {"$unwind": "$sentiment_data"},
            # Project final shape
            {
                "$project": {
                    "_id": 0,
                    "id": 1,
                    "title": "$content.title",
                    "description": "$content.description",
                    "source": 1,
                    "url": 1,
                    "publishedAt": 1,
                    "relatedSymbols": 1,
                    "sentiment": "$sentiment_data.label",
                    "sentiment_score": "$sentiment_data.score"
                }
            },
            # Sort and limit
            {"$sort": {"publishedAt": -1}},
            {"$limit": limit}
        ]

        cursor = news_collection.aggregate(pipeline)
        return await cursor.to_list(length=limit)
    except Exception as e:
        print(f"Error retrieving news from MongoDB: {e}")
        raise

# Your existing API endpoints...
@app.get("/")
async def root():
    return {
        "message": "Welcome to News Sentiment Analysis API",
        "mongodb_status": "connected" if client else "disconnected"
    }

@app.get("/health")
async def health_check():
    try:
        await client.admin.command('ping')
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "mongodb_status": "connected",
            "database": "news_sentiment_db",
            "collections": ["news_articles", "sentiments", "content"]
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
        symbol_list = symbols.split(',') if symbols else None
        cache_key = f"news:{symbols}:{page}:{limit}"

        if cache_key in news_cache:
            return news_cache[cache_key]

        db_news = await get_news_from_db(symbol_list, limit)
        if db_news:
            news_cache[cache_key] = db_news
            return db_news

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
            await store_news_in_db(news_data)

            # Fetch the stored data to get the complete records
            processed_news = await get_news_from_db(symbol_list, limit)
            news_cache[cache_key] = processed_news
            return processed_news

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
            await store_news_in_db(news_data)

            # Return the processed news with sentiment
            return await get_news_from_db(
                symbols.split(',') if symbols else None,
                limit=10
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add a new endpoint to get sentiment statistics
@app.get("/api/sentiment/stats")
async def get_sentiment_stats(symbols: Optional[str] = None):
    try:
        match_query = {}
        if symbols:
            symbol_list = symbols.split(',')
            match_query["relatedSymbols"] = {"$in": symbol_list}

        pipeline = [
            {"$match": match_query},
            {
                "$lookup": {
                    "from": "sentiments",
                    "localField": "id",
                    "foreignField": "article_id",
                    "as": "sentiment"
                }
            },
            {"$unwind": "$sentiment"},
            {
                "$group": {
                    "_id": "$sentiment.label",
                    "count": {"$sum": 1},
                    "average_score": {"$avg": "$sentiment.score"}
                }
            }
        ]

        cursor = news_collection.aggregate(pipeline)
        stats = await cursor.to_list(length=None)

        return {
            "total_articles": sum(stat["count"] for stat in stats),
            "sentiment_distribution": {
                stat["_id"]: {
                    "count": stat["count"],
                    "average_score": round(stat["average_score"], 2)
                } for stat in stats
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Cleanup connection on shutdown
@app.on_event("shutdown")
async def shutdown_db_client():
    if client:
        client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 3000)), reload=True)
