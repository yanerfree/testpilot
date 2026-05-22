"use client";

import { useState, useEffect } from "react";
import { Calendar, Phone, MapPin } from "lucide-react";

interface Booking { id: number; customerName: string; phone: string; address: string | null; requirement: string | null; status: string; createdAt: string; }

const statusLabel: Record<string, { label: string; color: string }> = {
  pending: { label: "待处理", color: "bg-amber-100 text-amber-700" },
  contacted: { label: "已联系", color: "bg-blue-100 text-blue-700" },
  completed: { label: "已完成", color: "bg-green-100 text-green-700" },
};

export default function BookingsPage() {
  const [bookings, setBookings] = useState<Booking[]>([]);

  const load = async () => {
    const res = await fetch("/api/admin/bookings");
    if (res.ok) setBookings(await res.json());
  };

  useEffect(() => { load(); }, []);

  const updateStatus = async (id: number, status: string) => {
    await fetch(`/api/admin/bookings/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    load();
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6 flex items-center gap-2">
        <Calendar className="w-6 h-6 text-primary-500" /> 预约管理
      </h1>

      <div className="space-y-4">
        {bookings.length === 0 && <div className="bg-white rounded-xl border p-8 text-center text-gray-400">暂无预约</div>}
        {bookings.map((b) => {
          const st = statusLabel[b.status] || statusLabel.pending;
          return (
            <div key={b.id} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <span className="font-semibold text-gray-800">{b.customerName}</span>
                  <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${st.color}`}>{st.label}</span>
                </div>
                <span className="text-xs text-gray-400">{b.createdAt?.slice(0, 16).replace("T", " ")}</span>
              </div>
              <div className="flex flex-wrap gap-4 text-sm text-gray-600 mb-3">
                <span className="flex items-center gap-1"><Phone className="w-4 h-4" />{b.phone}</span>
                {b.address && <span className="flex items-center gap-1"><MapPin className="w-4 h-4" />{b.address}</span>}
              </div>
              {b.requirement && <p className="text-sm text-gray-500 bg-gray-50 rounded-lg p-3 mb-3">{b.requirement}</p>}
              <div className="flex gap-2">
                {b.status !== "contacted" && (
                  <button onClick={() => updateStatus(b.id, "contacted")} className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200">标记已联系</button>
                )}
                {b.status !== "completed" && (
                  <button onClick={() => updateStatus(b.id, "completed")} className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded-full hover:bg-green-200">标记已完成</button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
