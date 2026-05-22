"use client";

import { useState, useEffect } from "react";
import { Plus, Trash2, Edit, FileText } from "lucide-react";

interface ContentItem { id: number; type: string; title: string; body: string | null; images: string | null; isPublished: number; createdAt: string; }

const typeLabel: Record<string, string> = { plants: "绿植随拍", video: "视频动态", pets: "萌宠日常", quotes: "治愈短句", essays: "生活随笔" };

export default function ContentPage() {
  const [items, setItems] = useState<ContentItem[]>([]);
  const [filter, setFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<ContentItem | null>(null);
  const [form, setForm] = useState({ type: "plants", title: "", body: "", isPublished: 1 });

  const load = async () => {
    const params = filter ? `?type=${filter}` : "";
    const res = await fetch(`/api/admin/content${params}`);
    if (res.ok) setItems(await res.json());
  };

  useEffect(() => { load(); }, [filter]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const url = editing ? `/api/admin/content/${editing.id}` : "/api/admin/content";
    const method = editing ? "PUT" : "POST";
    await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) });
    setShowForm(false); setEditing(null); setForm({ type: "plants", title: "", body: "", isPublished: 1 }); load();
  };

  const startEdit = (item: ContentItem) => {
    setEditing(item);
    setForm({ type: item.type, title: item.title, body: item.body || "", isPublished: item.isPublished });
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除？")) return;
    await fetch(`/api/admin/content/${id}`, { method: "DELETE" });
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <FileText className="w-6 h-6 text-primary-500" /> 趣味内容管理
        </h1>
        <button onClick={() => { setShowForm(!showForm); setEditing(null); setForm({ type: "plants", title: "", body: "", isPublished: 1 }); }} className="flex items-center gap-1 px-3 py-2 bg-primary-600 hover:bg-primary-700 text-white text-sm rounded-lg">
          <Plus className="w-4 h-4" /> 新增内容
        </button>
      </div>

      <div className="flex gap-2 mb-4 flex-wrap">
        <button onClick={() => setFilter("")} className={`px-3 py-1 text-sm rounded-full border transition-colors ${!filter ? "bg-primary-100 border-primary-400 text-primary-700" : "border-gray-300"}`}>全部</button>
        {Object.entries(typeLabel).map(([k, v]) => (
          <button key={k} onClick={() => setFilter(k)} className={`px-3 py-1 text-sm rounded-full border transition-colors ${filter === k ? "bg-primary-100 border-primary-400 text-primary-700" : "border-gray-300"}`}>{v}</button>
        ))}
      </div>

      {showForm && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-lg">
                {Object.entries(typeLabel).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
              <input type="text" required placeholder="标题" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-lg md:col-span-2" />
            </div>
            <textarea placeholder="内容..." value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} rows={5} className="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none" />
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={!!form.isPublished} onChange={(e) => setForm({ ...form, isPublished: e.target.checked ? 1 : 0 })} />
              <span className="text-sm">发布</span>
            </label>
            <div className="flex gap-3">
              <button type="submit" className="px-6 py-2 bg-primary-600 text-white rounded-lg">{editing ? "更新" : "保存"}</button>
              <button type="button" onClick={() => { setShowForm(false); setEditing(null); }} className="px-6 py-2 bg-gray-100 text-gray-700 rounded-lg">取消</button>
            </div>
          </form>
        </div>
      )}

      <div className="space-y-3">
        {items.length === 0 && <div className="bg-white rounded-xl border p-8 text-center text-gray-400">暂无内容</div>}
        {items.map((item) => (
          <div key={item.id} className="bg-white rounded-xl border border-gray-200 p-4 flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="px-2 py-0.5 text-xs rounded-full bg-primary-50 text-primary-700">{typeLabel[item.type] || item.type}</span>
                {!item.isPublished && <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-500">草稿</span>}
              </div>
              <h3 className="font-medium text-gray-800 truncate">{item.title}</h3>
              <p className="text-xs text-gray-400">{item.createdAt?.slice(0, 16).replace("T", " ")}</p>
            </div>
            <div className="flex gap-2 ml-4">
              <button onClick={() => startEdit(item)} className="text-gray-400 hover:text-primary-600"><Edit className="w-4 h-4" /></button>
              <button onClick={() => handleDelete(item.id)} className="text-gray-400 hover:text-danger"><Trash2 className="w-4 h-4" /></button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
