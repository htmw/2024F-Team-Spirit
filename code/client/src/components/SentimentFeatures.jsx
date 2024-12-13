import React, { useState, useMemo } from "react";
import { Download } from "lucide-react";

const SentimentFeatures = ({ news }) => {
  const [sentimentFilter, setSentimentFilter] = useState("ALL");

  // Filter news based on sentiment
  const filteredNews = useMemo(() => {
    return news.filter((article) => {
      return sentimentFilter === "ALL" || article.sentiment === sentimentFilter;
    });
  }, [news, sentimentFilter]);

  // Export to CSV
  const exportToCSV = () => {
    const headers = [
      "Date",
      "Title",
      "Source",
      "Sentiment",
      "Sentiment Score",
      "Related Symbols",
      "URL",
    ];

    const csvData = filteredNews.map((article) => [
      new Date(article.publishedAt).toLocaleDateString(),
      article.title,
      article.source,
      article.sentiment,
      article.sentiment_score,
      article.relatedSymbols.join(", "),
      article.url,
    ]);

    const csvContent = [
      headers.join(","),
      ...csvData.map((row) => row.map((cell) => `"${cell}"`).join(",")),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `sentiment_analysis_${new Date().toISOString()}.csv`;
    link.click();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between p-4 bg-neutral-900 rounded-lg border border-neutral-800">
        <div className="flex items-center gap-3">
          <label className="text-xs font-mono text-neutral-400">
            Filter by Sentiment:
          </label>
          <select
            value={sentimentFilter}
            onChange={(e) => setSentimentFilter(e.target.value)}
            className="bg-neutral-800 border border-neutral-700 rounded px-3 py-1.5 text-sm font-mono"
          >
            <option value="ALL">All Sentiments</option>
            <option value="POSITIVE">Positive</option>
            <option value="NEUTRAL">Neutral</option>
            <option value="NEGATIVE">Negative</option>
          </select>
        </div>

        <button
          onClick={exportToCSV}
          className="flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-mono"
        >
          <Download className="w-4 h-4 mr-2" />
          Export CSV
        </button>
      </div>

      <div className="text-sm font-mono text-neutral-500">
        {filteredNews.length} articles match your filter
      </div>
    </div>
  );
};

export default SentimentFeatures;
