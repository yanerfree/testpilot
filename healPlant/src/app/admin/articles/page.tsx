"use client";

import { useState, useEffect } from "react";
import { BookOpen, Plus, Pencil, Trash2, X, Eye, EyeOff } from "lucide-react";

interface Article {
  id: number;
  title: string;
  body: string;
  category: string | null;
  coverImage: string | null;
  videoId: number | null;
  isPublished: number;
  createdAt: string;
  updatedAt: string;
}

const CATEGORY_MAP: Record<string, string> = {
  tips: "养护技巧",
  seasonal: "四季要点",
  pests: "病虫害",
  beginner: "新手入门",
};

const CATEGORIES = Object.entries(CATEGORY_MAP);

export default function ArticlesPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState<string>("all");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  // form fields
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [category, setCategory] = useState("");
  const [coverImage, setCoverImage] = useState("");
  const [isPublished, setIsPublished] = useState(true);

  const load = async (cat?: string) => {
    setLoading(true);
    const filter = cat && cat !== "all" ? `?category=${cat}` : "";
    try {
      const res = await fetch(`/api/admin/articles${filter}`);
      if (res.ok) setArticles(await res.json());
    } catch {
      // ignore
    }
    setLoading(false);
  };

  useEffect(() => { load(activeFilter); }, [activeFilter]);

  const resetForm = () => {
    setTitle("");
    setBody("");
    setCategory("");
    setCoverImage("");
    setIsPublished(true);
    setEditingId(null);
    setShowForm(false);
  };

  const openAdd = () => {
    resetForm();
    setShowForm(true);
  };

  const openEdit = (a: Article) => {
    setEditingId(a.id);
    setTitle(a.title);
    setBody(a.body);
    setCategory(a.category || "");
    setCoverImage(a.coverImage || "");
    setIsPublished(!!a.isPublished);
    setShowForm(true);
  };

  const handleSubmit = async () => {
    if (!title.trim()) return alert("请输入标题");
    if (!body.trim()) return alert("请输入内容");

    const payload = {
      title,
      body,
      category: category || null,
      coverImage: coverImage || null,
      isPublished,
    };

    if (editingId) {
      await fetch(`/api/admin/articles/${editingId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } else {
      await fetch("/api/admin/articles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }

    resetForm();
    load(activeFilter);
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除这篇文章？")) return;
    await fetch(`/api/admin/articles/${id}`, { method: "DELETE" });
    load(activeFilter);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <BookOpen className="w-6 h-6 text-primary-500" /> 科普文章管理
        </h1>
        <button onClick={openAdd} className="flex items-center gap-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm">
          <Plus className="w-4 h-4" /> 新增文章
        </button>
      </div>

      {/* Category filter tabs */}
      <div className="flex gap-2 mb-6 flex-wrap">
        <button
          onClick={() => setActiveFilter("all")}
          className={`px-4 py-1.5 rounded-full text-sm font-medium transition ${
            activeFilter === "all"
              ? "bg-primary-600 text-white"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          全部
        </button>
        {CATEGORIES.map(([key, label]) => (
          <button
            key={key}
            onClick={() => setActiveFilter(key)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition ${
              activeFilter === key
                ? "bg-primary-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Add / Edit Form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-700">
              {editingId ? "编辑文章" : "新增文章"}
            </h2>
            <button onClick={resetForm} className="text-gray-400 hover:text-gray-600">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">标题 *</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="文章标题"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-300 focus:border-primary-400 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">分类</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-300 focus:border-primary-400 outline-none"
              >
                <option value="">未分类</option>
                {CATEGORIES.map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-600 mb-1">封面图片 URL</label>
            <input
              type="text"
              value={coverImage}
              onChange={(e) => setCoverImage(e.target.value)}
              placeholder="https://... 或 /uploads/images/..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-300 focus:border-primary-400 outline-none"
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-600 mb-1">内容 *</label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="文章正文内容..."
              rows={12}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-300 focus:border-primary-400 outline-none resize-y font-mono"
            />
          </div>

          <div className="flex items-center gap-2 mb-4">
            <input
              type="checkbox"
              id="isPublished"
              checked={isPublished}
              onChange={(e) => setIsPublished(e.target.checked)}
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <label htmlFor="isPublished" className="text-sm text-gray-600">发布 (取消勾选则为草稿)</label>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleSubmit}
              className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm"
            >
              {editingId ? "保存修改" : "创建文章"}
            </button>
            <button onClick={resetForm} className="px-6 py-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 text-sm">
              取消
            </button>
          </div>
        </div>
      )}

      {/* Article List */}
      {loading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
          加载中...
        </div>
      ) : articles.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <BookOpen className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-400 mb-2">暂无文章</p>
          <p className="text-gray-300 text-sm">点击"新增文章"开始创作</p>
        </div>
      ) : (
        <div className="space-y-3">
          {articles.map((a) => (
            <div key={a.id} className={`bg-white rounded-xl border border-gray-200 p-5 ${!a.isPublished ? "opacity-70" : ""}`}>
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-medium text-gray-800 truncate">{a.title}</h3>
                  </div>
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    {a.category && (
                      <span className="px-2 py-0.5 bg-primary-50 text-primary-700 text-xs rounded-full">
                        {CATEGORY_MAP[a.category] || a.category}
                      </span>
                    )}
                    <span className={`px-2 py-0.5 text-xs rounded-full flex items-center gap-1 ${
                      a.isPublished
                        ? "bg-green-50 text-green-700"
                        : "bg-amber-50 text-amber-700"
                    }`}>
                      {a.isPublished ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                      {a.isPublished ? "已发布" : "草稿"}
                    </span>
                    <span className="text-xs text-gray-400">
                      {a.createdAt?.slice(0, 10)}
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 line-clamp-2">
                    {a.body?.slice(0, 120)}
                    {a.body?.length > 120 ? "..." : ""}
                  </p>
                </div>
                <div className="flex gap-2 ml-4 flex-shrink-0">
                  <button onClick={() => openEdit(a)} className="text-gray-400 hover:text-primary-600">
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button onClick={() => handleDelete(a.id)} className="text-gray-400 hover:text-danger">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
