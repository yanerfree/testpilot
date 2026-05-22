"use client";

import { useState, useEffect } from "react";
import { Wrench, Plus, Pencil, Trash2, X, Droplets, Scissors, Flower2, Bug, HeartPulse } from "lucide-react";

interface Service {
  id: number;
  name: string;
  description: string | null;
  price: string | null;
  icon: string | null;
  sortOrder: number;
  createdAt: string;
}

const ICON_OPTIONS = [
  { value: "droplets", label: "浇水", Icon: Droplets },
  { value: "scissors", label: "修剪", Icon: Scissors },
  { value: "flower2", label: "换盆", Icon: Flower2 },
  { value: "bug", label: "除虫", Icon: Bug },
  { value: "heart-pulse", label: "病害", Icon: HeartPulse },
];

const ICON_MAP: Record<string, typeof Droplets> = {
  droplets: Droplets,
  scissors: Scissors,
  flower2: Flower2,
  bug: Bug,
  "heart-pulse": HeartPulse,
};

function ServiceIcon({ icon, className }: { icon: string | null; className?: string }) {
  if (!icon) return <Wrench className={className} />;
  const IconComp = ICON_MAP[icon];
  if (!IconComp) return <Wrench className={className} />;
  return <IconComp className={className} />;
}

export default function ServicesPage() {
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  // form fields
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const [icon, setIcon] = useState("");
  const [sortOrder, setSortOrder] = useState(0);

  const load = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/services");
      if (res.ok) setServices(await res.json());
    } catch {
      // ignore
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const resetForm = () => {
    setName("");
    setDescription("");
    setPrice("");
    setIcon("");
    setSortOrder(0);
    setEditingId(null);
    setShowForm(false);
  };

  const openAdd = () => {
    resetForm();
    // Default sortOrder to max + 1
    const maxSort = services.reduce((m, s) => Math.max(m, s.sortOrder || 0), 0);
    setSortOrder(maxSort + 1);
    setShowForm(true);
  };

  const openEdit = (s: Service) => {
    setEditingId(s.id);
    setName(s.name);
    setDescription(s.description || "");
    setPrice(s.price || "");
    setIcon(s.icon || "");
    setSortOrder(s.sortOrder || 0);
    setShowForm(true);
  };

  const handleSubmit = async () => {
    if (!name.trim()) return alert("请输入服务名称");

    const payload = {
      name,
      description: description || null,
      price: price || null,
      icon: icon || null,
      sortOrder,
    };

    if (editingId) {
      await fetch(`/api/admin/services/${editingId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } else {
      await fetch("/api/admin/services", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }

    resetForm();
    load();
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除这个服务项目？")) return;
    await fetch(`/api/admin/services/${id}`, { method: "DELETE" });
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <Wrench className="w-6 h-6 text-primary-500" /> 服务项目管理
        </h1>
        <button onClick={openAdd} className="flex items-center gap-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm">
          <Plus className="w-4 h-4" /> 添加服务
        </button>
      </div>

      {/* Add / Edit Form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-700">
              {editingId ? "编辑服务" : "添加服务"}
            </h2>
            <button onClick={resetForm} className="text-gray-400 hover:text-gray-600">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">服务名称 *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例: 上门浇水"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-300 focus:border-primary-400 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">价格</label>
              <input
                type="text"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                placeholder="例: 单次 ¥30 起"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-300 focus:border-primary-400 outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">图标</label>
              <div className="flex gap-2 flex-wrap">
                {ICON_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setIcon(opt.value)}
                    className={`flex items-center gap-1.5 px-3 py-2 rounded-lg border text-sm transition ${
                      icon === opt.value
                        ? "border-primary-500 bg-primary-50 text-primary-700"
                        : "border-gray-200 text-gray-600 hover:border-gray-300"
                    }`}
                  >
                    <opt.Icon className="w-4 h-4" />
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">排序</label>
              <input
                type="number"
                value={sortOrder}
                onChange={(e) => setSortOrder(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-300 focus:border-primary-400 outline-none"
              />
              <p className="text-xs text-gray-400 mt-1">数字越小越靠前</p>
            </div>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-600 mb-1">服务描述</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="简要描述服务内容..."
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-300 focus:border-primary-400 outline-none resize-none"
            />
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleSubmit}
              className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm"
            >
              {editingId ? "保存修改" : "创建服务"}
            </button>
            <button onClick={resetForm} className="px-6 py-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 text-sm">
              取消
            </button>
          </div>
        </div>
      )}

      {/* Service List */}
      {loading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
          加载中...
        </div>
      ) : services.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <Wrench className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-400 mb-2">暂无服务项目</p>
          <p className="text-gray-300 text-sm">点击"添加服务"创建第一个服务</p>
        </div>
      ) : (
        <div className="space-y-3">
          {services.map((s) => (
            <div key={s.id} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  <div className="w-10 h-10 rounded-full bg-primary-50 flex items-center justify-center flex-shrink-0">
                    <ServiceIcon icon={s.icon} className="w-5 h-5 text-primary-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <h3 className="font-medium text-gray-800">{s.name}</h3>
                      {s.price && (
                        <span className="px-2 py-0.5 bg-amber-50 text-amber-700 text-xs rounded-full">
                          {s.price}
                        </span>
                      )}
                      <span className="px-2 py-0.5 bg-gray-100 text-gray-400 text-xs rounded-full">
                        #{s.sortOrder}
                      </span>
                    </div>
                    {s.description && (
                      <p className="text-sm text-gray-500 truncate">{s.description}</p>
                    )}
                  </div>
                </div>
                <div className="flex gap-2 ml-4 flex-shrink-0">
                  <button onClick={() => openEdit(s)} className="text-gray-400 hover:text-primary-600">
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button onClick={() => handleDelete(s.id)} className="text-gray-400 hover:text-danger">
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
