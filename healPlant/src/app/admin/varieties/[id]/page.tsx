"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Save, Trash2 } from "lucide-react";

interface Variety {
  id: number;
  name: string;
  appearance: string | null;
  difficulty: string | null;
  growthHabit: string | null;
  suitableScene: string | null;
  marketPrice: number | null;
  popularityRating: number | null;
  seasonalIndex: string | null;
  customerFeedback: string | null;
  showInFrontend: number;
  frontendDescription: string | null;
  coverImage: string | null;
}

interface PricingLogEntry {
  id: number;
  mode: string;
  manualPrice: number | null;
  markupPercent: number | null;
  calculatedPrice: number;
  baseCost: number | null;
  createdAt: string;
}

export default function VarietyDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [variety, setVariety] = useState<Variety | null>(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  // Pricing state
  const [pricingMode, setPricingMode] = useState<"manual" | "markup">("manual");
  const [manualPrice, setManualPrice] = useState("");
  const [markupPercent, setMarkupPercent] = useState("");
  const [calculatedPrice, setCalculatedPrice] = useState<number | null>(null);
  const [pricingHistory, setPricingHistory] = useState<PricingLogEntry[]>([]);
  const [pricingMsg, setPricingMsg] = useState("");

  const loadVariety = useCallback(async () => {
    const res = await fetch(`/api/admin/varieties/${id}`);
    if (res.ok) {
      setVariety(await res.json());
    }
  }, [id]);

  const loadPricing = useCallback(async () => {
    const res = await fetch(`/api/admin/varieties/${id}/pricing`);
    if (res.ok) {
      setPricingHistory(await res.json());
    }
  }, [id]);

  useEffect(() => {
    loadVariety();
    loadPricing();
  }, [loadVariety, loadPricing]);

  useEffect(() => {
    if (pricingMode === "markup" && markupPercent && variety?.marketPrice) {
      const cost = variety.marketPrice;
      const price = cost * (1 + parseFloat(markupPercent) / 100);
      setCalculatedPrice(Math.round(price * 100) / 100);
    } else {
      setCalculatedPrice(null);
    }
  }, [pricingMode, markupPercent, variety?.marketPrice]);

  const handleSave = async () => {
    if (!variety) return;
    setSaving(true);
    setMsg("");

    const seasonalIndex = variety.seasonalIndex
      ? (typeof variety.seasonalIndex === "string"
          ? (() => { try { return JSON.parse(variety.seasonalIndex); } catch { return []; } })()
          : variety.seasonalIndex)
      : [];

    const res = await fetch(`/api/admin/varieties/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...variety, seasonalIndex }),
    });

    setSaving(false);
    setMsg(res.ok ? "保存成功" : "保存失败");
    setTimeout(() => setMsg(""), 2000);
  };

  const handleSavePricing = async () => {
    setPricingMsg("");
    const body: Record<string, unknown> = { mode: pricingMode };

    if (pricingMode === "manual") {
      if (!manualPrice) return setPricingMsg("请输入售价");
      body.manualPrice = parseFloat(manualPrice);
    } else {
      if (!markupPercent) return setPricingMsg("请输入涨幅百分比");
      body.markupPercent = parseFloat(markupPercent);
    }

    const res = await fetch(`/api/admin/varieties/${id}/pricing`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (res.ok) {
      setPricingMsg("定价保存成功");
      setManualPrice("");
      setMarkupPercent("");
      loadPricing();
    } else {
      const data = await res.json();
      setPricingMsg(data.error || "保存失败");
    }
    setTimeout(() => setPricingMsg(""), 3000);
  };

  const handleDelete = async () => {
    if (!confirm("确定删除该品种？相关的进货、销售、定价记录都会一并删除！")) return;
    await fetch(`/api/admin/varieties/${id}`, { method: "DELETE" });
    router.push("/admin/varieties");
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("/api/admin/upload/image", {
      method: "POST",
      body: formData,
    });

    if (res.ok) {
      const data = await res.json();
      setVariety((prev) => prev ? { ...prev, coverImage: data.url } : prev);
    }
  };

  if (!variety) {
    return (
      <div className="flex items-center justify-center py-20 text-gray-400">
        加载中...
      </div>
    );
  }

  const seasons = (() => {
    try {
      return typeof variety.seasonalIndex === "string"
        ? JSON.parse(variety.seasonalIndex)
        : variety.seasonalIndex || [];
    } catch {
      return [];
    }
  })() as string[];

  const toggleSeason = (s: string) => {
    const next = seasons.includes(s)
      ? seasons.filter((x: string) => x !== s)
      : [...seasons, s];
    setVariety({ ...variety, seasonalIndex: JSON.stringify(next) });
  };

  return (
    <div className="max-w-4xl">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => router.push("/admin/varieties")}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-600" />
        </button>
        <h1 className="text-2xl font-bold text-gray-800 flex-1">
          {variety.name}
        </h1>
        <button
          onClick={handleDelete}
          className="flex items-center gap-1 px-3 py-2 text-sm text-danger hover:bg-red-50 rounded-lg transition-colors"
        >
          <Trash2 className="w-4 h-4" /> 删除
        </button>
      </div>

      {/* Basic Info */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h2 className="font-semibold text-gray-700 mb-4">基本信息</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="品种名称">
            <input
              type="text"
              value={variety.name}
              onChange={(e) => setVariety({ ...variety, name: e.target.value })}
              className="input-field"
            />
          </Field>
          <Field label="养护难度">
            <select
              value={variety.difficulty || "easy"}
              onChange={(e) => setVariety({ ...variety, difficulty: e.target.value })}
              className="input-field"
            >
              <option value="easy">容易</option>
              <option value="medium">中等</option>
              <option value="hard">困难</option>
            </select>
          </Field>
          <Field label="外形特征">
            <input
              type="text"
              value={variety.appearance || ""}
              onChange={(e) => setVariety({ ...variety, appearance: e.target.value })}
              className="input-field"
            />
          </Field>
          <Field label="生长习性">
            <input
              type="text"
              value={variety.growthHabit || ""}
              onChange={(e) => setVariety({ ...variety, growthHabit: e.target.value })}
              className="input-field"
            />
          </Field>
          <Field label="适用场景">
            <input
              type="text"
              value={variety.suitableScene || ""}
              onChange={(e) => setVariety({ ...variety, suitableScene: e.target.value })}
              className="input-field"
            />
          </Field>
          <Field label="市场进价 (元)">
            <input
              type="number"
              step="0.01"
              value={variety.marketPrice ?? ""}
              onChange={(e) =>
                setVariety({
                  ...variety,
                  marketPrice: e.target.value ? parseFloat(e.target.value) : null,
                })
              }
              className="input-field"
            />
          </Field>
          <Field label="热度等级">
            <select
              value={variety.popularityRating || 3}
              onChange={(e) =>
                setVariety({ ...variety, popularityRating: parseInt(e.target.value) })
              }
              className="input-field"
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {"★".repeat(n)}{"☆".repeat(5 - n)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="畅销季节">
            <div className="flex gap-2 pt-1">
              {["spring", "summer", "autumn", "winter"].map((s) => {
                const labels: Record<string, string> = {
                  spring: "春",
                  summer: "夏",
                  autumn: "秋",
                  winter: "冬",
                };
                return (
                  <button
                    key={s}
                    type="button"
                    onClick={() => toggleSeason(s)}
                    className={`px-3 py-1 text-sm rounded-full border transition-colors ${
                      seasons.includes(s)
                        ? "bg-primary-100 border-primary-400 text-primary-700"
                        : "bg-white border-gray-300 text-gray-500"
                    }`}
                  >
                    {labels[s]}
                  </button>
                );
              })}
            </div>
          </Field>
          <div className="md:col-span-2">
            <Field label="顾客反馈记录">
              <textarea
                value={variety.customerFeedback || ""}
                onChange={(e) =>
                  setVariety({ ...variety, customerFeedback: e.target.value })
                }
                rows={2}
                className="input-field resize-none"
              />
            </Field>
          </div>
        </div>

        {/* Cover image */}
        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            封面图
          </label>
          <div className="flex items-center gap-4">
            {variety.coverImage && (
              <img
                src={variety.coverImage}
                alt="封面"
                className="w-20 h-20 object-cover rounded-lg border"
              />
            )}
            <label className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-sm text-gray-700 rounded-lg cursor-pointer transition-colors">
              上传图片
              <input
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
              />
            </label>
          </div>
        </div>

        {/* Frontend display toggle */}
        <div className="mt-4 p-4 bg-primary-50 rounded-lg">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={!!variety.showInFrontend}
              onChange={(e) =>
                setVariety({ ...variety, showInFrontend: e.target.checked ? 1 : 0 })
              }
              className="w-4 h-4 text-primary-600 rounded"
            />
            <span className="text-sm font-medium text-primary-700">
              在前台产品展示页显示此品种
            </span>
          </label>
          {!!variety.showInFrontend && (
            <textarea
              placeholder="前台公开描述（面向顾客展示，不含成本信息）"
              value={variety.frontendDescription || ""}
              onChange={(e) =>
                setVariety({ ...variety, frontendDescription: e.target.value })
              }
              rows={2}
              className="mt-3 w-full px-3 py-2 border border-primary-200 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none resize-none text-sm"
            />
          )}
        </div>

        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? "保存中..." : "保存修改"}
          </button>
          {msg && (
            <span className={`text-sm ${msg.includes("成功") ? "text-success" : "text-danger"}`}>
              {msg}
            </span>
          )}
        </div>
      </div>

      {/* Pricing Panel */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h2 className="font-semibold text-gray-700 mb-4">💰 智能定价</h2>

        <div className="space-y-4">
          {/* Mode selector */}
          <div className="flex gap-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="pricingMode"
                checked={pricingMode === "manual"}
                onChange={() => setPricingMode("manual")}
                className="text-primary-600"
              />
              <span className="text-sm font-medium">手动输入售价</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="pricingMode"
                checked={pricingMode === "markup"}
                onChange={() => setPricingMode("markup")}
                className="text-primary-600"
              />
              <span className="text-sm font-medium">成本涨幅定价</span>
            </label>
          </div>

          {/* Manual mode */}
          {pricingMode === "manual" && (
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-600">售价 ¥</span>
              <input
                type="number"
                step="0.01"
                value={manualPrice}
                onChange={(e) => setManualPrice(e.target.value)}
                placeholder="输入售卖价格"
                className="w-40 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              />
            </div>
          )}

          {/* Markup mode */}
          {pricingMode === "markup" && (
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-600">涨幅</span>
                <input
                  type="number"
                  step="1"
                  value={markupPercent}
                  onChange={(e) => setMarkupPercent(e.target.value)}
                  placeholder="如 80"
                  className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
                />
                <span className="text-sm text-gray-600">%</span>
              </div>
              {variety.marketPrice != null && (
                <p className="text-sm text-gray-500">
                  当前参考进价: ¥{variety.marketPrice.toFixed(2)}
                </p>
              )}
              {calculatedPrice != null && (
                <p className="text-lg font-semibold text-primary-600">
                  计算售价: ¥{calculatedPrice.toFixed(2)}
                </p>
              )}
              {!variety.marketPrice && (
                <p className="text-sm text-amber-600">
                  ⚠ 请先设置市场进价或录入进货记录
                </p>
              )}
            </div>
          )}

          <div className="flex items-center gap-3">
            <button
              onClick={handleSavePricing}
              className="px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors"
            >
              保存定价
            </button>
            {pricingMsg && (
              <span
                className={`text-sm ${
                  pricingMsg.includes("成功") ? "text-success" : "text-danger"
                }`}
              >
                {pricingMsg}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Pricing History */}
      {pricingHistory.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="font-semibold text-gray-700 mb-4">📋 定价历史</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-3 py-2 text-left text-gray-600">时间</th>
                  <th className="px-3 py-2 text-left text-gray-600">模式</th>
                  <th className="px-3 py-2 text-left text-gray-600">参数</th>
                  <th className="px-3 py-2 text-right text-gray-600">售价</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {pricingHistory.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="px-3 py-2 text-gray-500">
                      {log.createdAt?.slice(0, 16).replace("T", " ")}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`px-2 py-0.5 text-xs rounded-full ${
                          log.mode === "manual"
                            ? "bg-blue-100 text-blue-700"
                            : "bg-purple-100 text-purple-700"
                        }`}
                      >
                        {log.mode === "manual" ? "手动" : "涨幅"}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-600">
                      {log.mode === "manual"
                        ? `直接定价 ¥${log.manualPrice?.toFixed(2)}`
                        : `进价 ¥${log.baseCost?.toFixed(2)} × ${(100 + (log.markupPercent || 0)).toFixed(0)}%`}
                    </td>
                    <td className="px-3 py-2 text-right font-medium text-primary-600">
                      ¥{log.calculatedPrice.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <style jsx>{`
        .input-field {
          width: 100%;
          padding: 0.5rem 0.75rem;
          border: 1px solid #d1d5db;
          border-radius: 0.5rem;
          outline: none;
          transition: all 0.15s;
        }
        .input-field:focus {
          border-color: #4caf50;
          box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
        }
      `}</style>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
      </label>
      {children}
    </div>
  );
}
