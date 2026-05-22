"use client";

import { useState, useEffect } from "react";

export default function AboutPage() {
  const [content, setContent] = useState("");

  useEffect(() => {
    fetch("/api/public/about")
      .then((r) => r.json())
      .then((data) => {
        if (data?.content) setContent(data.content);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-primary-800 mb-8 text-center">
        关于我
      </h1>
      <div className="bg-white rounded-xl shadow-sm p-8">
        {content ? (
          <div
            className="prose prose-green max-w-none text-gray-600 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: content }}
          />
        ) : (
          <p className="text-gray-400 text-center">暂无内容</p>
        )}
      </div>
    </div>
  );
}
