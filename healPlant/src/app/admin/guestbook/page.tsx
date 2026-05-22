"use client";

import { useState, useEffect } from "react";
import { Trash2, Reply, MessageSquare } from "lucide-react";

interface Entry { id: number; nickname: string; message: string; adminReply: string | null; isVisible: number; createdAt: string; }

export default function GuestbookManagePage() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [replyingId, setReplyingId] = useState<number | null>(null);
  const [replyText, setReplyText] = useState("");

  const load = async () => {
    const res = await fetch("/api/admin/guestbook");
    if (res.ok) setEntries(await res.json());
  };

  useEffect(() => { load(); }, []);

  const handleReply = async (id: number) => {
    if (!replyText.trim()) return;
    await fetch(`/api/admin/guestbook/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ adminReply: replyText.trim() }),
    });
    setReplyingId(null);
    setReplyText("");
    load();
  };

  const handleToggleVisible = async (entry: Entry) => {
    await fetch(`/api/admin/guestbook/${entry.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ isVisible: entry.isVisible ? 0 : 1 }),
    });
    load();
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除？")) return;
    await fetch(`/api/admin/guestbook/${id}`, { method: "DELETE" });
    load();
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6 flex items-center gap-2">
        <MessageSquare className="w-6 h-6 text-primary-500" /> 留言管理
      </h1>

      <div className="space-y-4">
        {entries.length === 0 && <div className="bg-white rounded-xl border p-8 text-center text-gray-400">暂无留言</div>}
        {entries.map((e) => (
          <div key={e.id} className={`bg-white rounded-xl border p-5 ${!e.isVisible ? "opacity-60" : ""}`}>
            <div className="flex items-start justify-between mb-2">
              <div>
                <span className="font-medium text-primary-700">{e.nickname}</span>
                <span className="text-xs text-gray-400 ml-2">{e.createdAt?.slice(0, 16).replace("T", " ")}</span>
                {!e.isVisible && <span className="ml-2 px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded-full">已隐藏</span>}
              </div>
              <div className="flex gap-2">
                <button onClick={() => handleToggleVisible(e)} className="text-xs px-2 py-1 border rounded text-gray-500 hover:bg-gray-50">
                  {e.isVisible ? "隐藏" : "显示"}
                </button>
                <button onClick={() => { setReplyingId(e.id); setReplyText(e.adminReply || ""); }} className="text-gray-400 hover:text-primary-600"><Reply className="w-4 h-4" /></button>
                <button onClick={() => handleDelete(e.id)} className="text-gray-400 hover:text-danger"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>
            <p className="text-sm text-gray-600 mb-2">{e.message}</p>
            {e.adminReply && (
              <div className="bg-primary-50 rounded-lg p-3 border-l-4 border-primary-400 mb-2">
                <p className="text-xs text-primary-600 font-medium mb-1">管理员回复</p>
                <p className="text-sm text-gray-700">{e.adminReply}</p>
              </div>
            )}
            {replyingId === e.id && (
              <div className="flex gap-2 mt-2">
                <input type="text" value={replyText} onChange={(ev) => setReplyText(ev.target.value)} placeholder="输入回复..." className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                <button onClick={() => handleReply(e.id)} className="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg">回复</button>
                <button onClick={() => setReplyingId(null)} className="px-4 py-2 bg-gray-100 text-gray-600 text-sm rounded-lg">取消</button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
