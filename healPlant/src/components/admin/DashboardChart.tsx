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
} from "recharts";

interface TrendPoint {
  date: string;
  profit: number;
  revenue: number;
}

export default function DashboardChart() {
  const [data, setData] = useState<TrendPoint[]>([]);

  useEffect(() => {
    const now = new Date();
    const from = new Date(now.getTime() - 7 * 86400000)
      .toISOString()
      .split("T")[0];
    const to = now.toISOString().split("T")[0];

    fetch(`/api/admin/sales?dateFrom=${from}&dateTo=${to}`)
      .then((r) => r.json())
      .then((sales) => {
        const byDate: Record<string, { revenue: number; profit: number }> = {};
        for (const s of sales) {
          if (!byDate[s.saleDate])
            byDate[s.saleDate] = { revenue: 0, profit: 0 };
          byDate[s.saleDate].revenue += s.totalRevenue;
          byDate[s.saleDate].profit += s.profit;
        }
        setData(
          Object.entries(byDate)
            .map(([date, v]) => ({ date: date.slice(5), ...v }))
            .sort((a, b) => a.date.localeCompare(b.date))
        );
      })
      .catch(() => {});
  }, []);

  if (data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="font-semibold text-gray-700 mb-4">近 7 天利润趋势</h2>
        <div className="h-[200px] flex items-center justify-center text-gray-400 text-sm">
          暂无销售数据
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="font-semibold text-gray-700 mb-4">近 7 天利润趋势</h2>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="date" fontSize={12} />
          <YAxis fontSize={12} />
          <Tooltip formatter={(v) => `¥${Number(v).toFixed(2)}`} />
          <Line
            type="monotone"
            dataKey="profit"
            stroke="#4CAF50"
            strokeWidth={2}
            name="利润"
            dot={{ r: 3 }}
          />
          <Line
            type="monotone"
            dataKey="revenue"
            stroke="#81C784"
            strokeWidth={2}
            name="营收"
            strokeDasharray="5 5"
            dot={{ r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
