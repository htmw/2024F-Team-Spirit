import React, { useState, useEffect } from "react";
import { Search, Plus, X, RefreshCw, ExternalLink } from "lucide-react";

const API_BASE_URL = "http://localhost:3000/api";

const NewsCard = ({ article }) => (
  <div className="border-b border-neutral-800 py-4 hover:bg-neutral-900 px-4 -mx-4 transition-colors">
    <div className="flex items-center space-x-3 mb-2 font-mono text-xs">
      <span className="text-emerald-500">{article.source}</span>
      <span className="text-neutral-500">
        {new Date(article.publishedAt).toLocaleDateString()}
      </span>
      {article.relatedSymbols.map((symbol) => (
        <span key={symbol} className="text-blue-400">
          ${symbol}
        </span>
      ))}
    </div>
    <h3 className="text-neutral-100 text-base font-medium mb-2 leading-snug">
      {article.title}
    </h3>
    <div className="flex items-center justify-between">
      <p className="text-neutral-400 text-sm line-clamp-2 pr-4">
        {article.description}
      </p>
      <a
        href={article.url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-blue-400 hover:text-blue-300 flex items-center text-xs font-mono"
      >
        MORE <ExternalLink className="w-3 h-3 ml-1" />
      </a>
    </div>
  </div>
);

const StockSymbol = ({ symbol, onRemove }) => (
  <div className="inline-flex items-center bg-neutral-900 border border-neutral-800 px-2 py-1 rounded">
    <span className="font-mono text-sm text-blue-400">${symbol}</span>
    <button
      onClick={() => onRemove(symbol)}
      className="ml-2 text-neutral-500 hover:text-neutral-300"
    >
      <X className="w-3 h-3" />
    </button>
  </div>
);

export default function App() {
  const [symbols, setSymbols] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("all");
  const [currentTime, setCurrentTime] = useState(new Date());
  const [error, setError] = useState(null);

  // Time update effect
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Initial news fetch effect
  useEffect(() => {
    fetchNews();
  }, []);

  // Fetch news when symbols change
  useEffect(() => {
    if (symbols.length > 0) {
      fetchNews();
    }
  }, [symbols]);

  const fetchNews = async () => {
    try {
      setLoading(true);
      setError(null);
      const symbolsQuery =
        symbols.length > 0 ? `?symbols=${symbols.join(",")}` : "";
      const response = await fetch(`${API_BASE_URL}/news${symbolsQuery}`);

      if (!response.ok) {
        throw new Error("Failed to fetch news");
      }

      const data = await response.json();
      setNews(data);
    } catch (error) {
      console.error("Error fetching news:", error);
      setError("Failed to load news. Please try again later.");
    } finally {
      setLoading(false);
    }
  };

  const refreshNews = async () => {
    try {
      setLoading(true);
      setError(null);
      const symbolsQuery =
        symbols.length > 0 ? `?symbols=${symbols.join(",")}` : "";
      const response = await fetch(
        `${API_BASE_URL}/news/refresh${symbolsQuery}`,
      );

      if (!response.ok) {
        throw new Error("Failed to refresh news");
      }

      const data = await response.json();
      setNews(data);
    } catch (error) {
      console.error("Error refreshing news:", error);
      setError("Failed to refresh news. Please try again later.");
    } finally {
      setLoading(false);
    }
  };

  const addSymbol = (symbol) => {
    const formatted = symbol.trim().toUpperCase();
    if (formatted && !symbols.includes(formatted)) {
      setSymbols([...symbols, formatted]);
      setSearchTerm("");
    }
  };

  const removeSymbol = (symbol) => {
    setSymbols(symbols.filter((s) => s !== symbol));
  };

  const filteredNews = news.filter((article) => {
    if (filter === "all") return true;
    return filter === "relevant"
      ? article.relatedSymbols.some((symbol) => symbols.includes(symbol))
      : !article.relatedSymbols.some((symbol) => symbols.includes(symbol));
  });

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100">
      {/* Header */}
      <header className="bg-neutral-900 border-b border-neutral-800 sticky top-0 z-10">
        <div className="max-w-screen-xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-6">
              <h1 className="text-lg font-mono font-medium tracking-tight">
                MARKET NEWS
              </h1>
              <div className="h-4 w-px bg-neutral-800" />
              <div className="text-xs font-mono text-neutral-400">
                {currentTime.toLocaleTimeString()}
              </div>
            </div>
            <button
              onClick={refreshNews}
              disabled={loading || symbols.length === 0}
              className={`flex items-center px-3 py-1.5 text-xs font-mono
                bg-neutral-800 hover:bg-neutral-700 rounded
                ${loading || symbols.length === 0 ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              <RefreshCw
                className={`w-3 h-3 mr-2 ${loading ? "animate-spin" : ""}`}
              />
              REFRESH
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-screen-xl mx-auto px-4 py-6">
        {/* Search and Controls */}
        <div className="mb-8 space-y-4">
          <div className="relative">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && addSymbol(searchTerm)}
              placeholder="Add symbol..."
              className="w-full bg-neutral-900 border border-neutral-800 rounded
                px-3 py-2 text-sm font-mono placeholder:text-neutral-600
                focus:outline-none focus:border-blue-500"
            />
            <button
              onClick={() => addSymbol(searchTerm)}
              disabled={!searchTerm}
              className={`absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded
                ${searchTerm ? "text-blue-400 hover:text-blue-300" : "text-neutral-700"}`}
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex flex-wrap gap-2">
              {symbols.map((symbol) => (
                <StockSymbol
                  key={symbol}
                  symbol={symbol}
                  onRemove={removeSymbol}
                />
              ))}
            </div>

            <div className="flex items-center space-x-4">
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1
                  text-xs font-mono focus:outline-none focus:border-blue-500"
              >
                <option value="all">ALL NEWS</option>
                <option value="relevant">RELEVANT</option>
                <option value="other">OTHER</option>
              </select>

              <span className="text-xs font-mono text-neutral-500">
                {filteredNews.length} ITEMS
              </span>
            </div>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="text-center py-6 text-red-400 text-sm font-mono">
            {error}
          </div>
        )}

        {/* News Content */}
        {loading ? (
          <div className="text-center py-12">
            <RefreshCw className="w-8 h-8 text-blue-400 mx-auto mb-3 animate-spin" />
            <p className="text-sm font-mono text-neutral-500">LOADING NEWS</p>
          </div>
        ) : (
          <div className="divide-y divide-neutral-800">
            {filteredNews.map((article) => (
              <NewsCard key={article.id} article={article} />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && filteredNews.length === 0 && (
          <div className="text-center py-12">
            <Search className="w-8 h-8 text-neutral-700 mx-auto mb-3" />
            <p className="text-sm font-mono text-neutral-500">NO NEWS FOUND</p>
          </div>
        )}
      </main>
    </div>
  );
}
