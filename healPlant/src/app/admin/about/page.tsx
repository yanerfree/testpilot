"use client";

import { useState, useEffect } from "react";
import { Save, Info } from "lucide-react";

export default function AdminAboutPage() {
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    fetch("/api/admin/about")
      .then((r) => r.json())
      .then((data) => {
        if (data?.content) setContent(data.content);
      })
      .catch(() => {});
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setMsg("");
    const res = await fetch("/api/admin/about", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    setSaving(false);
    setMsg(res.ok ? "保存成功" : "保存失败");
    setTimeout(() => setMsg(""), 3000);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6 flex items-center gap-2">
        <Info className="w-6 h-6 text-primary-500" /> 简介管理
      </h1>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <p className="text-sm text-gray-500 mb-4">
          编辑个人简介页面内容，支持 HTML 格式。此内容将显示在前台"关于我"页面。
        </p>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={16}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none font-mono text-sm resize-y"
          placeholder="<h2>你好，我是一位绿植爱好者</h2>&#10;<p>正在武汉学习绿植养护技术...</p>"
        />
        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? "保存中..." : "保存"}
          </button>
          {msg && (
            <span className={`text-sm ${msg.includes("成功") ? "text-success" : "text-danger"}`}>
              {msg}
            </span>
          )}
        </div>
      </div>

      {content && (
        <div className="mt-6 bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-sm font-semibold text-gray-500 mb-3">预览效果</h3>
          <div
            className="prose prose-green max-w-none text-gray-600"
            dangerouslySetInnerHTML={{ __html: content }}
          />
        </div>
      )}
    </div>
  );
}
