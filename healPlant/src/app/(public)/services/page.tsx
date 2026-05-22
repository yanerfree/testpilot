import { db } from "@/lib/db";
import { service } from "@/lib/db/schema";
import { asc } from "drizzle-orm";
import { Droplets, Scissors, Flower2, Bug, HeartPulse } from "lucide-react";
import BookingForm from "@/components/public/BookingForm";

const iconMap: Record<string, React.ReactNode> = {
  droplets: <Droplets className="w-8 h-8" />,
  scissors: <Scissors className="w-8 h-8" />,
  flower2: <Flower2 className="w-8 h-8" />,
  bug: <Bug className="w-8 h-8" />,
  "heart-pulse": <HeartPulse className="w-8 h-8" />,
};

export default async function ServicesPage() {
  const services = await db.select().from(service).orderBy(asc(service.sortOrder));

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      {/* Hero */}
      <div className="bg-gradient-to-r from-primary-500 to-primary-700 rounded-2xl p-8 md:p-12 text-white text-center mb-12">
        <h1 className="text-3xl md:text-4xl font-bold mb-3">
          专业上门绿植养护
        </h1>
        <p className="text-white/80 text-lg">武汉本地 · 上门服务 · 专业细致</p>
      </div>

      {/* Services */}
      <h2 className="text-2xl font-bold text-gray-800 mb-6">服务项目</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
        {services.map((s) => (
          <div
            key={s.id}
            className="bg-white rounded-xl border border-gray-100 p-6 hover:shadow-md transition-shadow"
          >
            <div className="w-14 h-14 bg-primary-50 text-primary-600 rounded-xl flex items-center justify-center mb-4">
              {iconMap[s.icon || "flower2"] || <Flower2 className="w-8 h-8" />}
            </div>
            <h3 className="font-semibold text-lg text-gray-800 mb-2">
              {s.name}
            </h3>
            <p className="text-sm text-gray-500 mb-3">{s.description}</p>
            {s.price && (
              <span className="inline-block px-3 py-1 bg-primary-50 text-primary-700 text-sm rounded-full font-medium">
                {s.price}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Booking Form */}
      <BookingForm />

      {/* Contact */}
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center mt-12">
        <h2 className="text-xl font-bold text-gray-800 mb-2">联系我们</h2>
        <p className="text-gray-500 mb-4">
          如需咨询或预约服务，欢迎通过以下方式联系
        </p>
        <p className="text-primary-600 font-medium">
          微信 / 电话：请通过留言板联系获取
        </p>
      </div>
    </div>
  );
}
