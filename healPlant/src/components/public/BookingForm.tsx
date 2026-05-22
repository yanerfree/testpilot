"use client";

import { useState } from "react";
import { Send, CheckCircle } from "lucide-react";

export default function BookingForm() {
  const [form, setForm] = useState({
    customerName: "",
    phone: "",
    address: "",
    requirement: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!/^1[3-9]\d{9}$/.test(form.phone)) {
      setError("请输入正确的手机号");
      return;
    }

    setSubmitting(true);
    const res = await fetch("/api/public/bookings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    setSubmitting(false);

    if (res.ok) {
      setSubmitted(true);
      setForm({ customerName: "", phone: "", address: "", requirement: "" });
    } else {
      const data = await res.json();
      setError(data.error || "提交失败，请稍后重试");
    }
  };

  if (submitted) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center mt-12">
        <CheckCircle className="w-12 h-12 text-success mx-auto mb-4" />
        <h2 className="text-xl font-bold text-gray-800 mb-2">预约提交成功！</h2>
        <p className="text-gray-500 mb-4">我们会尽快与您联系，请保持电话畅通</p>
        <button
          onClick={() => setSubmitted(false)}
          className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          再次预约
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-8 mt-12">
      <h2 className="text-xl font-bold text-gray-800 mb-2 text-center">
        在线预约
      </h2>
      <p className="text-gray-500 text-center mb-6 text-sm">
        填写以下信息，我们将尽快与您联系
      </p>

      <form
        onSubmit={handleSubmit}
        className="max-w-lg mx-auto space-y-4"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              姓名 *
            </label>
            <input
              type="text"
              required
              value={form.customerName}
              onChange={(e) => setForm({ ...form, customerName: e.target.value })}
              placeholder="您的姓名"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              联系电话 *
            </label>
            <input
              type="tel"
              required
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              placeholder="手机号码"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            地址
          </label>
          <input
            type="text"
            value={form.address}
            onChange={(e) => setForm({ ...form, address: e.target.value })}
            placeholder="上门服务地址（武汉市内）"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            需求描述
          </label>
          <textarea
            value={form.requirement}
            onChange={(e) => setForm({ ...form, requirement: e.target.value })}
            placeholder="请描述您的养护需求，如植物种类、数量、问题等"
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none resize-none"
          />
        </div>

        {error && (
          <p className="text-sm text-danger text-center">{error}</p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-3 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
        >
          <Send className="w-4 h-4" />
          {submitting ? "提交中..." : "提交预约"}
        </button>
      </form>
    </div>
  );
}
