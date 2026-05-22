"use client";

import { useState, useEffect } from "react";
import { Plus, Search, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";

interface Variety {
  id: number;
  name: string;
  difficulty: string | null;
  marketPrice: number | null;
  popularityRating: number | null;
  showInFrontend: number;
}

export default function VarietiesPage() {
  const router = useRouter();
  const [varieties, setVarieties] = useState<Variety[]>([]);
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "",
    appearance: "",
    difficulty: "easy",
    growthHabit: "",
    suitableScene: "",
    marketPrice: "",
    popularityRating: "3",
    customerFeedback: "",
  });

  const loadVarieties = async () => {
    const params = search ? `?search=${encodeURIComponent(search)}` : "";
    const res = await fetch(`/api/admin/varieties${params}`);
    if (res.ok) setVarieties(await res.json());
  };

  useEffect(() => {
    loadVarieties();
  }, [search]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await fetch("/api/admin/varieties", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...form,
        marketPrice: form.marketPrice ? parseFloat(form.marketPrice) : null,
        popularityRating: parseInt(form.popularityRating),
      }),
    });
    if (res.ok) {
      setShowForm(false);
      setForm({
        name: "",
        appearance: "",
        difficulty: "easy",
        growthHabit: "",
        suitableScene: "",
        marketPrice: "",
        popularityRating: "3",
        customerFeedback: "",
      });
      loadVarieties();
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除该品种？")) return;
    await fetch(`/api/admin/varieties/${id}`, { method: "DELETE" });
    loadVarieties();
  };

  const difficultyLabel: Record<string, string> = {
    easy: "容易",
    medium: "中等",
    hard: "困难",
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">品种资料库</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          新增品种
        </button>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="搜索品种名称..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
        />
      </div>

      {/* Add Form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h2 className="font-semibold text-gray-700 mb-4">新增品种</h2>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                品种名称 *
              </label>
              <input
                type="text"
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                养护难度
              </label>
              <select
                value={form.difficulty}
                onChange={(e) => setForm({ ...form, difficulty: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              >
                <option value="easy">容易</option>
                <option value="medium">中等</option>
                <option value="hard">困难</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                市场进价 (元)
              </label>
              <input
                type="number"
                step="0.01"
                value={form.marketPrice}
                onChange={(e) => setForm({ ...form, marketPrice: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                热度等级 (1-5)
              </label>
              <select
                value={form.popularityRating}
                onChange={(e) => setForm({ ...form, popularityRating: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              >
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>
                    {"★".repeat(n)}{"☆".repeat(5 - n)}
                  </option>
                ))}
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                外形特征
              </label>
              <input
                type="text"
                value={form.appearance}
                onChange={(e) => setForm({ ...form, appearance: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                生长习性
              </label>
              <input
                type="text"
                value={form.growthHabit}
                onChange={(e) => setForm({ ...form, growthHabit: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                适用场景
              </label>
              <input
                type="text"
                value={form.suitableScene}
                onChange={(e) => setForm({ ...form, suitableScene: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              />
            </div>
            <div className="md:col-span-2 flex gap-3">
              <button
                type="submit"
                className="px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors"
              >
                保存
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-6 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-lg transition-colors"
              >
                取消
              </button>
            </div>
          </form>
        </div>
      )}

      {/* List */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">名称</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">难度</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">进价</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">热度</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">前台展示</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {varieties.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                    暂无品种数据
                  </td>
                </tr>
              )}
              {varieties.map((v) => (
                <tr key={v.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => router.push(`/admin/varieties/${v.id}`)}>
                  <td className="px-4 py-3 font-medium text-gray-800">
                    {v.name}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {v.difficulty ? difficultyLabel[v.difficulty] || v.difficulty : "-"}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {v.marketPrice != null ? `¥${v.marketPrice.toFixed(2)}` : "-"}
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-gold">
                      {"★".repeat(v.popularityRating || 0)}
                      {"☆".repeat(5 - (v.popularityRating || 0))}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 text-xs rounded-full ${
                        v.showInFrontend
                          ? "bg-green-100 text-green-700"
                          : "bg-gray-100 text-gray-500"
                      }`}
                    >
                      {v.showInFrontend ? "展示" : "隐藏"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleDelete(v.id)}
                      className="p-1 text-gray-400 hover:text-danger transition-colors"
                      title="删除"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
