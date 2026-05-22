"use client";

import { useState, useEffect } from "react";
import { Video, Upload, Pencil, Trash2, Plus, X, Eye, EyeOff } from "lucide-react";

interface VideoItem {
  id: number;
  title: string;
  description: string | null;
  filePath: string;
  thumbnailPath: string | null;
  category: string | null;
  duration: number | null;
  isPublic: number;
  createdAt: string;
  updatedAt: string;
}

const CATEGORY_MAP: Record<string, string> = {
  care: "养护",
  timelapse: "延时",
  fun: "趣味",
  pets: "萌宠",
  shop: "店铺",
};

const CATEGORIES = Object.entries(CATEGORY_MAP);

export default function VideosPage() {
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState("");
  const [uploadedUrl, setUploadedUrl] = useState("");

  // form fields
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [isPublic, setIsPublic] = useState(true);
  const [videoFile, setVideoFile] = useState<File | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/videos");
      if (res.ok) setVideos(await res.json());
    } catch {
      // API may not be ready yet
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const resetForm = () => {
    setTitle("");
    setDescription("");
    setCategory("");
    setIsPublic(true);
    setVideoFile(null);
    setUploadedUrl("");
    setUploadProgress("");
    setEditingId(null);
    setShowForm(false);
  };

  const openAdd = () => {
    resetForm();
    setShowForm(true);
  };

  const openEdit = (v: VideoItem) => {
    setEditingId(v.id);
    setTitle(v.title);
    setDescription(v.description || "");
    setCategory(v.category || "");
    setIsPublic(!!v.isPublic);
    setUploadedUrl(v.filePath);
    setVideoFile(null);
    setUploadProgress("");
    setShowForm(true);
  };

  const handleUploadFile = async () => {
    if (!videoFile) return;
    setUploading(true);
    setUploadProgress("正在上传视频...");

    const formData = new FormData();
    formData.append("file", videoFile);

    try {
      const res = await fetch("/api/admin/upload/video", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        setUploadProgress(`上传失败: ${err.error || "未知错误"}`);
        setUploading(false);
        return;
      }

      const data = await res.json();
      setUploadedUrl(data.url);
      setUploadProgress("上传成功!");
    } catch {
      setUploadProgress("上传失败: 网络错误");
    }
    setUploading(false);
  };

  const handleSubmit = async () => {
    if (!title.trim()) return alert("请输入标题");

    const filePath = uploadedUrl;
    if (!filePath && !editingId) return alert("请先上传视频文件");

    if (editingId) {
      await fetch(`/api/admin/videos/${editingId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, description, category: category || null, isPublic }),
      });
    } else {
      await fetch("/api/admin/videos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, description, filePath, category: category || null, isPublic }),
      });
    }

    resetForm();
    load();
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除这个视频？")) return;
    await fetch(`/api/admin/videos/${id}`, { method: "DELETE" });
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <Video className="w-6 h-6 text-primary-500" /> 视频管理
        </h1>
        <button onClick={openAdd} className="flex items-center gap-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm">
          <Plus className="w-4 h-4" /> 添加视频
        </button>
      </div>

      {/* Add / Edit Form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-700">
              {editingId ? "编辑视频" : "添加视频"}
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
                placeholder="视频标题"
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
            <label className="block text-sm font-medium text-gray-600 mb-1">描述</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="视频描述 (可选)"
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-300 focus:border-primary-400 outline-none resize-none"
            />
          </div>

          <div className="flex items-center gap-2 mb-4">
            <input
              type="checkbox"
              id="isPublic"
              checked={isPublic}
              onChange={(e) => setIsPublic(e.target.checked)}
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <label htmlFor="isPublic" className="text-sm text-gray-600">公开可见</label>
          </div>

          {/* Upload section - only for new videos */}
          {!editingId && (
            <div className="mb-4 p-4 border-2 border-dashed border-gray-300 rounded-lg">
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg cursor-pointer text-sm text-gray-700">
                  <Upload className="w-4 h-4" />
                  选择视频文件
                  <input
                    type="file"
                    accept="video/*"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) {
                        setVideoFile(f);
                        setUploadProgress("");
                        setUploadedUrl("");
                      }
                    }}
                  />
                </label>
                {videoFile && (
                  <span className="text-sm text-gray-500">
                    {videoFile.name} ({(videoFile.size / 1024 / 1024).toFixed(1)} MB)
                  </span>
                )}
              </div>
              {videoFile && !uploadedUrl && (
                <button
                  onClick={handleUploadFile}
                  disabled={uploading}
                  className="mt-3 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                  {uploading ? "上传中..." : "开始上传"}
                </button>
              )}
              {uploadProgress && (
                <p className={`mt-2 text-sm ${uploadedUrl ? "text-green-600" : "text-gray-500"}`}>
                  {uploadProgress}
                </p>
              )}
              {uploadedUrl && (
                <p className="mt-1 text-xs text-gray-400 break-all">文件路径: {uploadedUrl}</p>
              )}
            </div>
          )}

          {editingId && uploadedUrl && (
            <p className="mb-4 text-xs text-gray-400 break-all">当前文件: {uploadedUrl}</p>
          )}

          <div className="flex gap-2">
            <button
              onClick={handleSubmit}
              disabled={uploading}
              className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm disabled:opacity-50"
            >
              {editingId ? "保存修改" : "创建视频"}
            </button>
            <button onClick={resetForm} className="px-6 py-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 text-sm">
              取消
            </button>
          </div>
        </div>
      )}

      {/* Video Grid */}
      {loading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
          加载中...
        </div>
      ) : videos.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <Video className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-400 mb-2">暂无视频</p>
          <p className="text-gray-300 text-sm">点击上方"添加视频"开始上传</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {videos.map((v) => (
            <div key={v.id} className={`bg-white rounded-xl border border-gray-200 overflow-hidden ${!v.isPublic ? "opacity-70" : ""}`}>
              {/* Thumbnail placeholder */}
              <div className="h-36 bg-gray-100 flex items-center justify-center">
                <span className="text-4xl">🎬</span>
              </div>
              <div className="p-4">
                <h3 className="font-medium text-gray-800 text-sm mb-2 truncate">{v.title}</h3>
                {v.description && (
                  <p className="text-xs text-gray-400 mb-2 line-clamp-2">{v.description}</p>
                )}
                <div className="flex items-center gap-2 mb-3">
                  {v.category && (
                    <span className="px-2 py-0.5 bg-primary-50 text-primary-700 text-xs rounded-full">
                      {CATEGORY_MAP[v.category] || v.category}
                    </span>
                  )}
                  <span className={`px-2 py-0.5 text-xs rounded-full flex items-center gap-1 ${v.isPublic ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {v.isPublic ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                    {v.isPublic ? "公开" : "隐藏"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400">
                    {v.createdAt?.slice(0, 10)}
                  </span>
                  <div className="flex gap-2">
                    <button onClick={() => openEdit(v)} className="text-gray-400 hover:text-primary-600">
                      <Pencil className="w-4 h-4" />
                    </button>
                    <button onClick={() => handleDelete(v.id)} className="text-gray-400 hover:text-danger">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
