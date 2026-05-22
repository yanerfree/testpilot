"use client";

import { useState, useEffect } from "react";
import { Plus, Trash2, Filter } from "lucide-react";

interface Variety {
  id: number;
  name: string;
}

interface SaleRecord {
  id: number;
  varietyId: number;
  quantity: number;
  unitSalePrice: number;
  totalRevenue: number;
  costBasis: number;
  profit: number;
  saleDate: string;
  note: string | null;
}

export default function SalesPage() {
  const [records, setRecords] = useState<SaleRecord[]>([]);
  const [varieties, setVarieties] = useState<Variety[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [form, setForm] = useState({
    varietyId: "",
    quantity: "",
    unitSalePrice: "",
    saleDate: new Date().toISOString().split("T")[0],
    note: "",
  });

  const loadRecords = async () => {
    const params = new URLSearchParams();
    if (dateFrom) params.set("dateFrom", dateFrom);
    if (dateTo) params.set("dateTo", dateTo);
    const qs = params.toString();
    const res = await fetch(`/api/admin/sales${qs ? `?${qs}` : ""}`);
    if (res.ok) setRecords(await res.json());
  };

  const loadVarieties = async () => {
    const res = await fetch("/api/admin/varieties");
    if (res.ok) setVarieties(await res.json());
  };

  useEffect(() => {
    loadVarieties();
  }, []);

  useEffect(() => {
    loadRecords();
  }, [dateFrom, dateTo]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await fetch("/api/admin/sales", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        varietyId: parseInt(form.varietyId),
        quantity: parseInt(form.quantity),
        unitSalePrice: parseFloat(form.unitSalePrice),
        saleDate: form.saleDate,
        note: form.note || null,
      }),
    });
    if (res.ok) {
      setShowForm(false);
      setForm({
        varietyId: "",
        quantity: "",
        unitSalePrice: "",
        saleDate: new Date().toISOString().split("T")[0],
        note: "",
      });
      loadRecords();
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除该销售记录？")) return;
    await fetch(`/api/admin/sales/${id}`, { method: "DELETE" });
    loadRecords();
  };

  const varietyName = (id: number) => {
    const v = varieties.find((v) => v.id === id);
    return v ? v.name : `品种#${id}`;
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">销售台账</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          新增
        </button>
      </div>

      {/* Date Range Filter */}
      <div className="flex items-center gap-3 mb-4">
        <Filter className="w-4 h-4 text-gray-400" />
        <input
          type="date"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none text-sm"
          placeholder="开始日期"
        />
        <span className="text-gray-400">至</span>
        <input
          type="date"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none text-sm"
          placeholder="结束日期"
        />
        {(dateFrom || dateTo) && (
          <button
            onClick={() => {
              setDateFrom("");
              setDateTo("");
            }}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            清除
          </button>
        )}
      </div>

      {/* Add Form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h2 className="font-semibold text-gray-700 mb-4">新增销售记录</h2>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                品种 *
              </label>
              <select
                required
                value={form.varietyId}
                onChange={(e) => setForm({ ...form, varietyId: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              >
                <option value="">请选择品种</option>
                {varieties.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                数量 *
              </label>
              <input
                type="number"
                required
                min="1"
                value={form.quantity}
                onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                售价 (元) *
              </label>
              <input
                type="number"
                required
                step="0.01"
                min="0"
                value={form.unitSalePrice}
                onChange={(e) => setForm({ ...form, unitSalePrice: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                销售日期 *
              </label>
              <input
                type="date"
                required
                value={form.saleDate}
                onChange={(e) => setForm({ ...form, saleDate: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                备注
              </label>
              <input
                type="text"
                value={form.note}
                onChange={(e) => setForm({ ...form, note: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
                placeholder="可选"
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

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">品种ID</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">数量</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">售价(¥)</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">总营收(¥)</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">利润(¥)</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">日期</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {records.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                    暂无销售记录
                  </td>
                </tr>
              )}
              {records.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">
                    {varietyName(r.varietyId)}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{r.quantity}</td>
                  <td className="px-4 py-3 text-gray-600">¥{r.unitSalePrice.toFixed(2)}</td>
                  <td className="px-4 py-3 text-gray-800 font-medium">¥{r.totalRevenue.toFixed(2)}</td>
                  <td className={`px-4 py-3 font-medium ${r.profit >= 0 ? "text-success" : "text-danger"}`}>
                    {r.profit >= 0 ? "+" : ""}¥{r.profit.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{r.saleDate}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleDelete(r.id)}
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
