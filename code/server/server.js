const express = require('express');
const cors = require('cors');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');
const axios = require('axios');
require('dotenv').config();

const app = express();

// Middleware
app.use(cors());
app.use(express.json());
app.use(morgan('dev'));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100
});
app.use(limiter);

// Cache configuration
const newsCache = new Map();
const CACHE_DURATION = 5 * 60 * 1000;

// Marketaux API configuration
const MARKETAUX_API = {
  baseURL: 'https://api.marketaux.com/v1',
  token: process.env.MARKETAUX_API_TOKEN,
  defaultParams: {
    language: 'en',
    filter_entities: true,
  }
};

// Transform to match frontend format
function transformNewsData(marketauxResponse) {
  return marketauxResponse.data.map(article => ({
    id: article.uuid,
    title: article.title,
    description: article.description || article.snippet,
    source: article.source,
    url: article.url,
    publishedAt: article.published_at,
    relatedSymbols: article.entities
      .filter(entity => entity.type === 'equity')
      .map(entity => entity.symbol)
  }));
}

// Routes
// GET /api/news - Get all news with optional symbol filtering
app.get('/api/news', async (req, res) => {
  try {
    const symbols = req.query.symbols?.split(',') || [];
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 10;

    const cacheKey = `news:${symbols.join(',')}:${page}:${limit}`;
    const cachedData = newsCache.get(cacheKey);
    
    if (cachedData && (Date.now() - cachedData.timestamp < CACHE_DURATION)) {
      return res.json(cachedData.data);
    }

    const response = await axios.get(`${MARKETAUX_API.baseURL}/news/all`, {
      params: {
        symbols: symbols.join(','),
        filter_entities: true,
        language: 'en',
        api_token: MARKETAUX_API.token,
        page,
        limit
      }
    });

    const transformedNews = transformNewsData(response.data);
    
    newsCache.set(cacheKey, {
      timestamp: Date.now(),
      data: transformedNews
    });

    res.json(transformedNews);
  } catch (error) {
    console.error('Error fetching news:', error);
    res.status(500).json({
      error: 'Failed to fetch news'
    });
  }
});

// GET /api/news/refresh - Force refresh news data
app.get('/api/news/refresh', async (req, res) => {
  try {
    const symbols = req.query.symbols?.split(',') || [];
    const response = await axios.get(`${MARKETAUX_API.baseURL}/news/all`, {
      params: {
        symbols: symbols.join(','),
        filter_entities: true,
        language: 'en',
        api_token: MARKETAUX_API.token,
        limit: 10
      }
    });

    const transformedNews = transformNewsData(response.data);
    res.json(transformedNews);
  } catch (error) {
    console.error('Error refreshing news:', error);
    res.status(500).json({
      error: 'Failed to refresh news'
    });
  }
});

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});