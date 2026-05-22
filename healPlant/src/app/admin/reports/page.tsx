"use client";

import { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  ShoppingCart,
  AlertTriangle,
  Percent,
} from "lucide-react";

interface Summary {
  totalPurchase: number;
  totalRevenue: number;
  totalProfit: number;
  grossMargin: number;
  totalWasted: number;
  totalLoss: number;
  wastageRate: number;
  balance: number;
}

export default function ReportsPage() {
  const today = new Date().toISOString().split("T")[0];
  const monthStart = today.slice(0, 7) + "-01";

  const [dateFrom, setDateFrom] = useState(monthStart);
  const [dateTo, setDateTo] = useState(today);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [salesTrend, setSalesTrend] = useState<{ date: string; revenue: number; profit: number }[]>([]);
  const [pieData, setPieData] = useState<{ name: string; revenue: number }[]>([]);

  useEffect(() => {
    fetch(`/api/admin/reports/summary?dateFrom=${dateFrom}&dateTo=${dateTo}`)
      .then((r) => r.json())
      .then(setSummary)
      .catch(() => {});

    fetch(`/api/admin/sales?dateFrom=${dateFrom}&dateTo=${dateTo}`)
      .then((r) => r.json())
      .then((data) => {
        const byDate: Record<string, { revenue: number; profit: number }> = {};
        const byVariety: Record<number, { name: string; revenue: number }> = {};
        for (const s of data) {
          if (!byDate[s.saleDate]) byDate[s.saleDate] = { revenue: 0, profit: 0 };
          byDate[s.saleDate].revenue += s.totalRevenue;
          byDate[s.saleDate].profit += s.profit;
          if (!byVariety[s.varietyId]) byVariety[s.varietyId] = { name: `品种${s.varietyId}`, revenue: 0 };
          byVariety[s.varietyId].revenue += s.totalRevenue;
        }
        setSalesTrend(
          Object.entries(byDate)
            .map(([date, v]) => ({ date: date.slice(5), ...v }))
            .sort((a, b) => a.date.localeCompare(b.date))
        );
        setPieData(Object.values(byVariety));
      })
      .catch(() => {});
  }, [dateFrom, dateTo]);

  const COLORS = ["#4CAF50", "#66BB6A", "#81C784", "#A5D6A7", "#C8E6C9", "#FFB74D", "#F8BBD0"];

  const quickRange = (key: string) => {
    const now = new Date();
    let from: string;
    if (key === "today") from = today;
    else if (key === "week") from = new Date(now.getTime() - 7 * 86400000).toISOString().split("T")[0];
    else if (key === "month") from = today.slice(0, 7) + "-01";
    else from = today.slice(0, 4) + "-01-01";
    setDateFrom(from);
    setDateTo(today);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">经营报表</h1>

      {/* Time Range */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm text-gray-600">时间:</span>
          {[{ label: "今日", key: "today" }, { label: "近7天", key: "week" }, { label: "本月", key: "month" }, { label: "全年", key: "year" }].map((btn) => (
            <button key={btn.key} onClick={() => quickRange(btn.key)} className="px-3 py-1 text-sm rounded-full border border-gray-300 hover:bg-primary-50 hover:border-primary-400 hover:text-primary-700 transition-colors">
              {btn.label}
            </button>
          ))}
          <div className="flex items-center gap-2 ml-auto">
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="px-2 py-1 border border-gray-300 rounded text-sm" />
            <span className="text-gray-400">至</span>
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="px-2 py-1 border border-gray-300 rounded text-sm" />
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <MetricCard icon={<ShoppingCart className="w-5 h-5" />} label="总进货成本" value={`¥${summary.totalPurchase.toFixed(2)}`} color="text-gray-700" bg="bg-gray-50" />
          <MetricCard icon={<DollarSign className="w-5 h-5" />} label="总销售额" value={`¥${summary.totalRevenue.toFixed(2)}`} color="text-primary-600" bg="bg-primary-50" />
          <MetricCard icon={<TrendingUp className="w-5 h-5" />} label="总利润" value={`¥${summary.totalProfit.toFixed(2)}`} color={summary.totalProfit >= 0 ? "text-success" : "text-danger"} bg={summary.totalProfit >= 0 ? "bg-green-50" : "bg-red-50"} />
          <MetricCard icon={<Percent className="w-5 h-5" />} label="毛利率" value={`${summary.grossMargin}%`} color={summary.grossMargin >= 0 ? "text-success" : "text-danger"} bg="bg-blue-50" />
          <MetricCard icon={<AlertTriangle className="w-5 h-5" />} label="损耗数量" value={`${summary.totalWasted} 盆`} color="text-amber-600" bg="bg-amber-50" />
          <MetricCard icon={<TrendingDown className="w-5 h-5" />} label="损耗率" value={`${summary.wastageRate}%`} color="text-amber-600" bg="bg-amber-50" />
          <MetricCard icon={<DollarSign className="w-5 h-5" />} label="损耗成本" value={`¥${summary.totalLoss.toFixed(2)}`} color="text-danger" bg="bg-red-50" />
          <MetricCard icon={<DollarSign className="w-5 h-5" />} label="资金结余" value={`¥${summary.balance.toFixed(2)}`} color={summary.balance >= 0 ? "text-success" : "text-danger"} bg={summary.balance >= 0 ? "bg-green-50" : "bg-red-50"} />
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-700 mb-4">利润趋势</h3>
          {salesTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={salesTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" fontSize={12} />
                <YAxis fontSize={12} />
                <Tooltip formatter={(v) => `¥${Number(v).toFixed(2)}`} />
                <Line type="monotone" dataKey="profit" stroke="#4CAF50" strokeWidth={2} name="利润" dot={{ r: 4 }} />
                <Line type="monotone" dataKey="revenue" stroke="#81C784" strokeWidth={2} name="营收" dot={{ r: 4 }} strokeDasharray="5 5" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[280px] flex items-center justify-center text-gray-400">暂无数据</div>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-700 mb-4">品种销售占比</h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" labelLine={false} label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`} outerRadius={100} dataKey="revenue" nameKey="name">
                  {pieData.map((_, i) => (<Cell key={`c-${i}`} fill={COLORS[i % COLORS.length]} />))}
                </Pie>
                <Tooltip formatter={(v) => `¥${Number(v).toFixed(2)}`} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[280px] flex items-center justify-center text-gray-400">暂无数据</div>
          )}
        </div>
      </div>
    </div>
  );
}

function MetricCard({ icon, label, value, color, bg }: { icon: React.ReactNode; label: string; value: string; color: string; bg: string }) {
  return (
    <div className={`${bg} rounded-xl p-4`}>
      <div className={`${color} mb-1`}>{icon}</div>
      <p className="text-xs text-gray-500 mb-0.5">{label}</p>
      <p className={`text-lg font-bold ${color}`}>{value}</p>
    </div>
  );
}
