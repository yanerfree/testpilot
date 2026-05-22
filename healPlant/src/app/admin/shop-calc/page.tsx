"use client";

import { useState, useEffect } from "react";
import { Plus, Trash2, Calculator } from "lucide-react";

interface CostItem {
  id: number;
  name: string;
  amount: number;
  frequency: string;
  category: string | null;
  monthlyAmount: number;
}

interface Revenue {
  optimistic: number;
  moderate: number;
  conservative: number;
  initialInvestment: number | null;
}

const freqLabel: Record<string, string> = { monthly: "月", quarterly: "季", yearly: "年" };
const catLabel: Record<string, string> = { rent: "租金", utility: "水电", labor: "人工", seedling: "种苗", other: "其他" };

export default function ShopCalcPage() {
  const [costs, setCosts] = useState<CostItem[]>([]);
  const [revenue, setRevenue] = useState<Revenue>({ optimistic: 0, moderate: 0, conservative: 0, initialInvestment: null });
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", amount: "", frequency: "monthly", category: "rent" });
  const [msg, setMsg] = useState("");

  const loadData = async () => {
    const [costsRes, revRes] = await Promise.all([
      fetch("/api/admin/shop-calc"),
      fetch("/api/admin/shop-calc/revenue"),
    ]);
    if (costsRes.ok) setCosts(await costsRes.json());
    if (revRes.ok) {
      const data = await revRes.json();
      if (data) setRevenue(data);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleAddCost = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await fetch("/api/admin/shop-calc", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, amount: parseFloat(form.amount) }),
    });
    if (res.ok) {
      setShowForm(false);
      setForm({ name: "", amount: "", frequency: "monthly", category: "rent" });
      loadData();
    }
  };

  const handleDeleteCost = async (id: number) => {
    if (!confirm("确定删除？")) return;
    await fetch(`/api/admin/shop-calc/${id}`, { method: "DELETE" });
    loadData();
  };

  const handleSaveRevenue = async () => {
    const res = await fetch("/api/admin/shop-calc/revenue", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(revenue),
    });
    setMsg(res.ok ? "保存成功" : "保存失败");
    setTimeout(() => setMsg(""), 2000);
  };

  const totalMonthly = costs.reduce((s, c) => s + c.monthlyAmount, 0);
  const monthlyProfit = (scenario: number) => scenario - totalMonthly;
  const paybackMonths = (scenario: number) => {
    const profit = monthlyProfit(scenario);
    if (profit <= 0 || !revenue.initialInvestment) return "N/A";
    return Math.ceil(revenue.initialInvestment / profit) + " 个月";
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">实体小店收支测算</h1>

      {/* Cost Items */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-700">成本项目</h2>
          <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-1 px-3 py-1.5 bg-primary-600 hover:bg-primary-700 text-white text-sm rounded-lg transition-colors">
            <Plus className="w-4 h-4" /> 新增
          </button>
        </div>

        {showForm && (
          <form onSubmit={handleAddCost} className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4 p-4 bg-gray-50 rounded-lg">
            <input type="text" required placeholder="名称" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-lg text-sm" />
            <input type="number" required step="0.01" placeholder="金额" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-lg text-sm" />
            <select value={form.frequency} onChange={(e) => setForm({ ...form, frequency: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
              <option value="monthly">月付</option>
              <option value="quarterly">季付</option>
              <option value="yearly">年付</option>
            </select>
            <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
              <option value="rent">租金</option>
              <option value="utility">水电</option>
              <option value="labor">人工</option>
              <option value="seedling">种苗</option>
              <option value="other">其他</option>
            </select>
            <button type="submit" className="col-span-2 md:col-span-4 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg">保存</button>
          </form>
        )}

        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-3 py-2 text-left text-gray-600">名称</th>
              <th className="px-3 py-2 text-left text-gray-600">类别</th>
              <th className="px-3 py-2 text-right text-gray-600">金额</th>
              <th className="px-3 py-2 text-left text-gray-600">频率</th>
              <th className="px-3 py-2 text-right text-gray-600">月均</th>
              <th className="px-3 py-2 text-right text-gray-600">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {costs.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50">
                <td className="px-3 py-2">{c.name}</td>
                <td className="px-3 py-2 text-gray-500">{catLabel[c.category || "other"] || c.category}</td>
                <td className="px-3 py-2 text-right">¥{c.amount.toFixed(2)}</td>
                <td className="px-3 py-2">{freqLabel[c.frequency] || c.frequency}</td>
                <td className="px-3 py-2 text-right font-medium">¥{c.monthlyAmount.toFixed(2)}</td>
                <td className="px-3 py-2 text-right">
                  <button onClick={() => handleDeleteCost(c.id)} className="text-gray-400 hover:text-danger"><Trash2 className="w-4 h-4" /></button>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot className="border-t-2">
            <tr className="font-bold">
              <td colSpan={4} className="px-3 py-2 text-right">月总支出:</td>
              <td className="px-3 py-2 text-right text-danger">¥{totalMonthly.toFixed(2)}</td>
              <td></td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Revenue Estimates */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h2 className="font-semibold text-gray-700 mb-4">营收预估</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">乐观预估 (月)</label>
            <input type="number" step="0.01" value={revenue.optimistic || ""} onChange={(e) => setRevenue({ ...revenue, optimistic: parseFloat(e.target.value) || 0 })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="¥" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">中性预估 (月)</label>
            <input type="number" step="0.01" value={revenue.moderate || ""} onChange={(e) => setRevenue({ ...revenue, moderate: parseFloat(e.target.value) || 0 })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="¥" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">保守预估 (月)</label>
            <input type="number" step="0.01" value={revenue.conservative || ""} onChange={(e) => setRevenue({ ...revenue, conservative: parseFloat(e.target.value) || 0 })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="¥" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">初始投入</label>
            <input type="number" step="0.01" value={revenue.initialInvestment || ""} onChange={(e) => setRevenue({ ...revenue, initialInvestment: parseFloat(e.target.value) || null })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="¥" />
          </div>
        </div>
        <div className="flex items-center gap-3 mt-4">
          <button onClick={handleSaveRevenue} className="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg">保存预估</button>
          {msg && <span className="text-sm text-success">{msg}</span>}
        </div>
      </div>

      {/* Results */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
          <Calculator className="w-5 h-5 text-primary-500" /> 测算结果
        </h2>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-3 py-2 text-left text-gray-600">场景</th>
              <th className="px-3 py-2 text-right text-gray-600">月营收</th>
              <th className="px-3 py-2 text-right text-gray-600">月支出</th>
              <th className="px-3 py-2 text-right text-gray-600">月盈亏</th>
              <th className="px-3 py-2 text-right text-gray-600">回本周期</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {[
              { label: "🟢 乐观", val: revenue.optimistic },
              { label: "🟡 中性", val: revenue.moderate },
              { label: "🔴 保守", val: revenue.conservative },
            ].map((s) => (
              <tr key={s.label}>
                <td className="px-3 py-2 font-medium">{s.label}</td>
                <td className="px-3 py-2 text-right">¥{s.val.toFixed(2)}</td>
                <td className="px-3 py-2 text-right">¥{totalMonthly.toFixed(2)}</td>
                <td className={`px-3 py-2 text-right font-bold ${monthlyProfit(s.val) >= 0 ? "text-success" : "text-danger"}`}>
                  ¥{monthlyProfit(s.val).toFixed(2)}
                </td>
                <td className="px-3 py-2 text-right">{paybackMonths(s.val)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
