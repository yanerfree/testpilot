"use client";

import { useState, useEffect } from "react";

interface Product {
  id: number;
  name: string;
  frontendDescription: string | null;
  coverImage: string | null;
  difficulty: string | null;
  growthHabit: string | null;
  suitableScene: string | null;
}

const diffLabel: Record<string, string> = { easy: "容易", medium: "中等", hard: "困难" };

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);

  useEffect(() => {
    fetch("/api/public/products")
      .then((r) => r.json())
      .then(setProducts)
      .catch(() => {});
  }, []);

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-primary-800 mb-2 text-center">
        花卉盆栽展示
      </h1>
      <p className="text-center text-gray-500 mb-8">
        精选绿植实拍 · 习性介绍 · 供您挑选参考
      </p>

      {products.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center text-gray-400">
          暂无展示产品
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {products.map((p) => (
            <div
              key={p.id}
              className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow"
            >
              {p.coverImage ? (
                <img
                  src={p.coverImage}
                  alt={p.name}
                  className="w-full h-48 object-cover"
                />
              ) : (
                <div className="w-full h-48 bg-primary-50 flex items-center justify-center text-4xl">
                  🌿
                </div>
              )}
              <div className="p-5">
                <h3 className="font-semibold text-lg text-gray-800 mb-2">
                  {p.name}
                </h3>
                {p.difficulty && (
                  <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-primary-50 text-primary-700 mb-2">
                    养护难度: {diffLabel[p.difficulty] || p.difficulty}
                  </span>
                )}
                {p.frontendDescription && (
                  <p className="text-sm text-gray-500 mb-2">
                    {p.frontendDescription}
                  </p>
                )}
                {p.growthHabit && (
                  <p className="text-xs text-gray-400">
                    习性: {p.growthHabit}
                  </p>
                )}
                {p.suitableScene && (
                  <p className="text-xs text-gray-400">
                    适用: {p.suitableScene}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
