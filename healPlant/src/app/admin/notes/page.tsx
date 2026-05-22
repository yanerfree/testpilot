"use client";

import { useState, useEffect } from "react";
import { Plus, Trash2, Edit, BookOpen, Search } from "lucide-react";

interface Note { id: number; title: string; body: string; tags: string | null; noteDate: string; createdAt: string; }

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Note | null>(null);
  const [form, setForm] = useState({ title: "", body: "", tags: "", noteDate: new Date().toISOString().split("T")[0] });

  const load = async () => {
    const params = search ? `?search=${encodeURIComponent(search)}` : "";
    const res = await fetch(`/api/admin/notes${params}`);
    if (res.ok) setNotes(await res.json());
  };

  useEffect(() => { load(); }, [search]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const url = editing ? `/api/admin/notes/${editing.id}` : "/api/admin/notes";
    const method = editing ? "PUT" : "POST";
    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, tags: form.tags ? JSON.stringify(form.tags.split(",").map(t => t.trim())) : null }),
    });
    if (res.ok) { setShowForm(false); setEditing(null); setForm({ title: "", body: "", tags: "", noteDate: new Date().toISOString().split("T")[0] }); load(); }
  };

  const startEdit = (n: Note) => {
    setEditing(n);
    let tags = "";
    try { tags = n.tags ? JSON.parse(n.tags).join(", ") : ""; } catch { tags = n.tags || ""; }
    setForm({ title: n.title, body: n.body, tags, noteDate: n.noteDate });
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除？")) return;
    await fetch(`/api/admin/notes/${id}`, { method: "DELETE" });
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <BookOpen className="w-6 h-6 text-primary-500" /> 学习台账
        </h1>
        <button onClick={() => { setShowForm(!showForm); setEditing(null); setForm({ title: "", body: "", tags: "", noteDate: new Date().toISOString().split("T")[0] }); }} className="flex items-center gap-1 px-3 py-2 bg-primary-600 hover:bg-primary-700 text-white text-sm rounded-lg">
          <Plus className="w-4 h-4" /> 写笔记
        </button>
      </div>

      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input type="text" placeholder="搜索笔记..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm" />
      </div>

      {showForm && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h2 className="font-semibold text-gray-700 mb-4">{editing ? "编辑笔记" : "写新笔记"}</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <input type="text" required placeholder="标题" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-lg" />
              <input type="date" value={form.noteDate} onChange={(e) => setForm({ ...form, noteDate: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-lg" />
            </div>
            <textarea placeholder="笔记内容..." value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} rows={6} className="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none" required />
            <input type="text" placeholder="标签（逗号分隔，如：养护技巧, 进货经验）" value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
            <div className="flex gap-3">
              <button type="submit" className="px-6 py-2 bg-primary-600 text-white rounded-lg">{editing ? "更新" : "保存"}</button>
              <button type="button" onClick={() => { setShowForm(false); setEditing(null); }} className="px-6 py-2 bg-gray-100 text-gray-700 rounded-lg">取消</button>
            </div>
          </form>
        </div>
      )}

      <div className="space-y-4">
        {notes.length === 0 && <div className="bg-white rounded-xl border p-8 text-center text-gray-400">暂无笔记</div>}
        {notes.map((n) => {
          let tags: string[] = [];
          try { tags = n.tags ? JSON.parse(n.tags) : []; } catch { /* ignore */ }
          return (
            <div key={n.id} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h3 className="font-semibold text-gray-800">{n.title}</h3>
                  <p className="text-xs text-gray-400">{n.noteDate}</p>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => startEdit(n)} className="text-gray-400 hover:text-primary-600"><Edit className="w-4 h-4" /></button>
                  <button onClick={() => handleDelete(n.id)} className="text-gray-400 hover:text-danger"><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
              <p className="text-sm text-gray-600 whitespace-pre-wrap mb-2">{n.body}</p>
              {tags.length > 0 && (
                <div className="flex gap-1 flex-wrap">
                  {tags.map((tag, i) => (
                    <span key={i} className="px-2 py-0.5 bg-primary-50 text-primary-700 text-xs rounded-full">{tag}</span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
