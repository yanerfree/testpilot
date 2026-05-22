"use client";

import { useState, useEffect } from "react";

interface ContentItem {
  id: number;
  type: string;
  title: string;
  body: string | null;
  images: string | null;
  createdAt: string;
}

const typeLabel: Record<string, string> = {
  plants: "🌱 绿植随拍",
  video: "🎬 视频动态",
  pets: "🐱 萌宠日常",
  quotes: "💬 治愈短句",
  essays: "📝 生活随笔",
};

const typeColors: Record<string, string> = {
  plants: "bg-green-100 text-green-700",
  video: "bg-blue-100 text-blue-700",
  pets: "bg-pink-100 text-pink-700",
  quotes: "bg-amber-100 text-amber-700",
  essays: "bg-purple-100 text-purple-700",
};

export default function FunPage() {
  const [items, setItems] = useState<ContentItem[]>([]);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    const params = filter ? `?type=${filter}` : "";
    fetch(`/api/public/content${params}`)
      .then((r) => r.json())
      .then(setItems)
      .catch(() => {});
  }, [filter]);

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-primary-800 mb-2 text-center">
        趣味生活广场
      </h1>
      <p className="text-center text-gray-500 mb-8">
        绿植随拍 · 视频动态 · 萌宠日常 · 治愈短句 · 生活随笔
      </p>

      {/* Tabs */}
      <div className="flex gap-2 justify-center mb-8 flex-wrap">
        <button
          onClick={() => setFilter("")}
          className={`px-4 py-2 text-sm rounded-full border transition-colors ${
            !filter
              ? "bg-primary-600 text-white border-primary-600"
              : "border-gray-300 hover:bg-gray-50"
          }`}
        >
          全部
        </button>
        {Object.entries(typeLabel).map(([k, v]) => (
          <button
            key={k}
            onClick={() => setFilter(k)}
            className={`px-4 py-2 text-sm rounded-full border transition-colors ${
              filter === k
                ? "bg-primary-600 text-white border-primary-600"
                : "border-gray-300 hover:bg-gray-50"
            }`}
          >
            {v}
          </button>
        ))}
      </div>

      {/* Content Grid */}
      {items.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center text-gray-400">
          暂无内容，管理员可在后台发布
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {items.map((item) => (
            <div
              key={item.id}
              className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow"
            >
              <div className="p-5">
                <span
                  className={`inline-block px-2 py-0.5 text-xs rounded-full mb-2 ${
                    typeColors[item.type] || "bg-gray-100 text-gray-600"
                  }`}
                >
                  {typeLabel[item.type] || item.type}
                </span>
                <h3 className="font-semibold text-gray-800 mb-2">
                  {item.title}
                </h3>
                {item.body && (
                  <p className="text-sm text-gray-500 line-clamp-3">
                    {item.body.replace(/<[^>]*>/g, "")}
                  </p>
                )}
                <p className="text-xs text-gray-400 mt-3">
                  {item.createdAt?.slice(0, 10)}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
