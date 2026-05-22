"use client";

import { useState, useEffect } from "react";
import { MessageSquare, Send } from "lucide-react";

interface GuestbookEntry {
  id: number;
  nickname: string;
  message: string;
  adminReply: string | null;
  createdAt: string;
}

export default function GuestbookPage() {
  const [entries, setEntries] = useState<GuestbookEntry[]>([]);
  const [nickname, setNickname] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    fetch("/api/public/guestbook")
      .then((r) => r.json())
      .then(setEntries)
      .catch(() => {});
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nickname.trim() || !message.trim()) return;
    setSubmitting(true);

    const res = await fetch("/api/public/guestbook", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nickname: nickname.trim(), message: message.trim() }),
    });

    setSubmitting(false);
    if (res.ok) {
      setSuccess(true);
      setNickname("");
      setMessage("");
      const updated = await fetch("/api/public/guestbook").then((r) => r.json());
      setEntries(updated);
      setTimeout(() => setSuccess(false), 3000);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-primary-800 mb-2 text-center">
        互动留言板
      </h1>
      <p className="text-center text-gray-500 mb-8">
        欢迎留言交流养花心得、提问养花问题
      </p>

      {/* Submit Form */}
      <div className="bg-white rounded-xl shadow-sm p-6 mb-8">
        <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-primary-500" />
          写下你的留言
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            placeholder="你的昵称"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
            required
          />
          <textarea
            placeholder="留言内容..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none resize-none"
            required
          />
          <div className="flex items-center gap-4">
            <button
              type="submit"
              disabled={submitting}
              className="px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              {submitting ? "提交中..." : "提交留言"}
            </button>
            {success && (
              <span className="text-sm text-success">留言成功！</span>
            )}
          </div>
        </form>
      </div>

      {/* Entries */}
      <div className="space-y-4">
        {entries.length === 0 && (
          <p className="text-center text-gray-400 py-8">
            暂无留言，来做第一个留言的人吧！
          </p>
        )}
        {entries.map((entry) => (
          <div
            key={entry.id}
            className="bg-white rounded-xl border border-gray-100 p-5"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="font-medium text-primary-700">
                {entry.nickname}
              </span>
              <span className="text-xs text-gray-400">
                {entry.createdAt?.slice(0, 16).replace("T", " ")}
              </span>
            </div>
            <p className="text-gray-600 mb-3">{entry.message}</p>
            {entry.adminReply && (
              <div className="bg-primary-50 rounded-lg p-3 border-l-4 border-primary-400">
                <p className="text-xs text-primary-600 font-medium mb-1">
                  管理员回复
                </p>
                <p className="text-sm text-gray-700">{entry.adminReply}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
