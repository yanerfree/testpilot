"use client";

import { useState, useEffect } from "react";

interface Article {
  id: number;
  title: string;
  body: string;
  category: string | null;
  coverImage: string | null;
  createdAt: string;
}

const catLabel: Record<string, string> = { tips: "养护技巧", seasonal: "四季要点", pests: "病虫害", beginner: "新手入门" };

export default function KnowledgePage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<Article | null>(null);

  useEffect(() => {
    const params = filter ? `?category=${filter}` : "";
    fetch(`/api/public/articles${params}`)
      .then((r) => r.json())
      .then(setArticles)
      .catch(() => {});
  }, [filter]);

  if (selected) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
        <button onClick={() => setSelected(null)} className="text-primary-600 hover:text-primary-700 mb-4 text-sm">
          ← 返回列表
        </button>
        <article className="bg-white rounded-xl shadow-sm p-8">
          <h1 className="text-2xl font-bold text-gray-800 mb-2">{selected.title}</h1>
          <p className="text-sm text-gray-400 mb-6">{selected.createdAt?.slice(0, 10)}</p>
          <div className="prose prose-green max-w-none text-gray-600" dangerouslySetInnerHTML={{ __html: selected.body }} />
        </article>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-primary-800 mb-2 text-center">养花科普专区</h1>
      <p className="text-center text-gray-500 mb-8">养护技巧 · 四季要点 · 病虫害处理 · 新手入门</p>

      <div className="flex gap-2 justify-center mb-8 flex-wrap">
        <button onClick={() => setFilter("")} className={`px-4 py-2 text-sm rounded-full border transition-colors ${!filter ? "bg-primary-600 text-white border-primary-600" : "border-gray-300"}`}>全部</button>
        {Object.entries(catLabel).map(([k, v]) => (
          <button key={k} onClick={() => setFilter(k)} className={`px-4 py-2 text-sm rounded-full border transition-colors ${filter === k ? "bg-primary-600 text-white border-primary-600" : "border-gray-300"}`}>{v}</button>
        ))}
      </div>

      {articles.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center text-gray-400">暂无文章</div>
      ) : (
        <div className="space-y-4">
          {articles.map((a) => (
            <div key={a.id} onClick={() => setSelected(a)} className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 cursor-pointer hover:shadow-md transition-shadow">
              <div className="flex items-start gap-4">
                {a.coverImage ? (
                  <img src={a.coverImage} alt="" className="w-24 h-24 object-cover rounded-lg flex-shrink-0" />
                ) : (
                  <div className="w-24 h-24 bg-primary-50 rounded-lg flex items-center justify-center text-2xl flex-shrink-0">📖</div>
                )}
                <div className="flex-1 min-w-0">
                  {a.category && <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-primary-50 text-primary-700 mb-1">{catLabel[a.category] || a.category}</span>}
                  <h3 className="font-semibold text-gray-800 mb-1">{a.title}</h3>
                  <p className="text-sm text-gray-500 line-clamp-2">{a.body.replace(/<[^>]*>/g, "")}</p>
                  <p className="text-xs text-gray-400 mt-2">{a.createdAt?.slice(0, 10)}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
