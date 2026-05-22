"use client";

import { useState, useEffect } from "react";
import { Plus, Trash2, Package } from "lucide-react";

interface InventoryItem {
  id: number;
  varietyId: number;
  varietyName: string | null;
  quantity: number;
  location: string | null;
  condition: string;
  category: string;
}

interface Variety { id: number; name: string; }

const condLabel: Record<string, string> = { good: "完好", "needs-care": "需养护", pending: "待处理" };
const catLabel: Record<string, string> = { "for-sale": "待售卖", "for-care": "待养护" };

export default function InventoryPage() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [varieties, setVarieties] = useState<Variety[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ varietyId: "", quantity: "", location: "", condition: "good", category: "for-sale" });

  const load = async () => {
    const [invRes, varRes] = await Promise.all([
      fetch("/api/admin/inventory"),
      fetch("/api/admin/varieties"),
    ]);
    if (invRes.ok) setItems(await invRes.json());
    if (varRes.ok) setVarieties(await varRes.json());
  };

  useEffect(() => { load(); }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await fetch("/api/admin/inventory", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, varietyId: parseInt(form.varietyId), quantity: parseInt(form.quantity) }),
    });
    if (res.ok) { setShowForm(false); setForm({ varietyId: "", quantity: "", location: "", condition: "good", category: "for-sale" }); load(); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除？")) return;
    await fetch(`/api/admin/inventory/${id}`, { method: "DELETE" });
    load();
  };

  const total = items.reduce((s, i) => s + i.quantity, 0);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <Package className="w-6 h-6 text-primary-500" /> 库存管理
          <span className="text-sm font-normal text-gray-500 ml-2">共 {total} 盆</span>
        </h1>
        <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-1 px-3 py-2 bg-primary-600 hover:bg-primary-700 text-white text-sm rounded-lg">
          <Plus className="w-4 h-4" /> 新增
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleAdd} className="bg-white rounded-xl border border-gray-200 p-4 mb-4 grid grid-cols-2 md:grid-cols-5 gap-3">
          <select required value={form.varietyId} onChange={(e) => setForm({ ...form, varietyId: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
            <option value="">选择品种</option>
            {varieties.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
          </select>
          <input type="number" required placeholder="数量" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          <input type="text" placeholder="摆放位置" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          <select value={form.condition} onChange={(e) => setForm({ ...form, condition: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
            <option value="good">完好</option>
            <option value="needs-care">需养护</option>
            <option value="pending">待处理</option>
          </select>
          <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
            <option value="for-sale">待售卖</option>
            <option value="for-care">待养护</option>
          </select>
          <button type="submit" className="col-span-2 md:col-span-5 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg">保存</button>
        </form>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left text-gray-600">品种</th>
              <th className="px-4 py-3 text-right text-gray-600">数量</th>
              <th className="px-4 py-3 text-left text-gray-600">位置</th>
              <th className="px-4 py-3 text-left text-gray-600">状态</th>
              <th className="px-4 py-3 text-left text-gray-600">分类</th>
              <th className="px-4 py-3 text-right text-gray-600">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {items.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">暂无库存</td></tr>}
            {items.map((item) => (
              <tr key={item.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{item.varietyName || `品种${item.varietyId}`}</td>
                <td className="px-4 py-3 text-right">{item.quantity}</td>
                <td className="px-4 py-3 text-gray-500">{item.location || "-"}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 text-xs rounded-full ${item.condition === "good" ? "bg-green-100 text-green-700" : item.condition === "needs-care" ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700"}`}>
                    {condLabel[item.condition] || item.condition}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500">{catLabel[item.category] || item.category}</td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => handleDelete(item.id)} className="text-gray-400 hover:text-danger"><Trash2 className="w-4 h-4" /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
