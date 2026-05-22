"use client";

import { useState, useEffect } from "react";
import { Eye, EyeOff, Flower2 } from "lucide-react";

interface Variety {
  id: number;
  name: string;
  difficulty: string | null;
  marketPrice: number | null;
  showInFrontend: number;
  frontendDescription: string | null;
  coverImage: string | null;
}

export default function ProductsDisplayPage() {
  const [varieties, setVarieties] = useState<Variety[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [desc, setDesc] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    const res = await fetch("/api/admin/varieties");
    if (res.ok) setVarieties(await res.json());
  };

  useEffect(() => { load(); }, []);

  const toggleShow = async (v: Variety) => {
    await fetch(`/api/admin/varieties/${v.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...v, showInFrontend: v.showInFrontend ? 0 : 1 }),
    });
    load();
  };

  const saveDesc = async (v: Variety) => {
    await fetch(`/api/admin/varieties/${v.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...v, frontendDescription: desc }),
    });
    setEditingId(null);
    setMsg("已保存");
    setTimeout(() => setMsg(""), 2000);
    load();
  };

  const visible = varieties.filter((v) => v.showInFrontend);
  const hidden = varieties.filter((v) => !v.showInFrontend);

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-2 flex items-center gap-2">
        <Flower2 className="w-6 h-6 text-primary-500" /> 产品展示管理
      </h1>
      <p className="text-sm text-gray-500 mb-6">
        控制哪些品种在前台产品展示页对外可见，并编辑面向顾客的公开描述。
        {msg && <span className="ml-2 text-success">{msg}</span>}
      </p>

      {/* Currently visible */}
      <h2 className="font-semibold text-gray-700 mb-3">
        前台展示中 ({visible.length})
      </h2>
      {visible.length === 0 ? (
        <div className="bg-white rounded-xl border p-6 text-center text-gray-400 mb-6">
          暂无展示品种，点击下方列表的"显示"按钮添加
        </div>
      ) : (
        <div className="space-y-3 mb-6">
          {visible.map((v) => (
            <VarietyCard
              key={v.id}
              variety={v}
              onToggle={() => toggleShow(v)}
              isEditing={editingId === v.id}
              onStartEdit={() => { setEditingId(v.id); setDesc(v.frontendDescription || ""); }}
              desc={desc}
              onDescChange={setDesc}
              onSaveDesc={() => saveDesc(v)}
              onCancelEdit={() => setEditingId(null)}
            />
          ))}
        </div>
      )}

      {/* Hidden */}
      <h2 className="font-semibold text-gray-700 mb-3">
        未展示 ({hidden.length})
      </h2>
      {hidden.length === 0 ? (
        <div className="bg-white rounded-xl border p-6 text-center text-gray-400">
          所有品种已展示
        </div>
      ) : (
        <div className="space-y-3">
          {hidden.map((v) => (
            <VarietyCard
              key={v.id}
              variety={v}
              onToggle={() => toggleShow(v)}
              isEditing={editingId === v.id}
              onStartEdit={() => { setEditingId(v.id); setDesc(v.frontendDescription || ""); }}
              desc={desc}
              onDescChange={setDesc}
              onSaveDesc={() => saveDesc(v)}
              onCancelEdit={() => setEditingId(null)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function VarietyCard({
  variety: v,
  onToggle,
  isEditing,
  onStartEdit,
  desc,
  onDescChange,
  onSaveDesc,
  onCancelEdit,
}: {
  variety: Variety;
  onToggle: () => void;
  isEditing: boolean;
  onStartEdit: () => void;
  desc: string;
  onDescChange: (s: string) => void;
  onSaveDesc: () => void;
  onCancelEdit: () => void;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {v.coverImage ? (
            <img src={v.coverImage} alt="" className="w-12 h-12 rounded-lg object-cover" />
          ) : (
            <div className="w-12 h-12 bg-primary-50 rounded-lg flex items-center justify-center text-xl">🌿</div>
          )}
          <div>
            <p className="font-medium text-gray-800">{v.name}</p>
            {v.frontendDescription && (
              <p className="text-xs text-gray-500 truncate max-w-xs">{v.frontendDescription}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onStartEdit}
            className="px-3 py-1 text-xs border border-gray-300 rounded-full hover:bg-gray-50"
          >
            编辑描述
          </button>
          <button
            onClick={onToggle}
            className={`flex items-center gap-1 px-3 py-1 text-xs rounded-full ${
              v.showInFrontend
                ? "bg-green-100 text-green-700 hover:bg-red-100 hover:text-red-700"
                : "bg-gray-100 text-gray-600 hover:bg-green-100 hover:text-green-700"
            }`}
          >
            {v.showInFrontend ? (
              <><Eye className="w-3 h-3" /> 隐藏</>
            ) : (
              <><EyeOff className="w-3 h-3" /> 显示</>
            )}
          </button>
        </div>
      </div>
      {isEditing && (
        <div className="mt-3 flex gap-2">
          <input
            type="text"
            value={desc}
            onChange={(e) => onDescChange(e.target.value)}
            placeholder="面向顾客的公开描述（不含价格信息）"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
          />
          <button onClick={onSaveDesc} className="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg">保存</button>
          <button onClick={onCancelEdit} className="px-4 py-2 bg-gray-100 text-gray-600 text-sm rounded-lg">取消</button>
        </div>
      )}
    </div>
  );
}
