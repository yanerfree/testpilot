import { db } from "@/lib/db";
import { sale, inventory, booking } from "@/lib/db/schema";
import { sql, gte } from "drizzle-orm";
import DashboardChart from "@/components/admin/DashboardChart";

export default async function AdminDashboard() {
  const today = new Date().toISOString().split("T")[0];
  const monthStart = today.slice(0, 7) + "-01";

  const [todaySales] = await db
    .select({ total: sql<number>`coalesce(sum(${sale.profit}), 0)` })
    .from(sale)
    .where(gte(sale.saleDate, today));

  const [monthRevenue] = await db
    .select({ total: sql<number>`coalesce(sum(${sale.totalRevenue}), 0)` })
    .from(sale)
    .where(gte(sale.saleDate, monthStart));

  const [inventoryCount] = await db
    .select({ total: sql<number>`coalesce(sum(${inventory.quantity}), 0)` })
    .from(inventory);

  const pendingBookings = await db
    .select()
    .from(booking)
    .where(sql`${booking.status} = 'pending'`);

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">
        欢迎回来 👋
      </h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="今日利润"
          value={`¥${todaySales.total.toFixed(2)}`}
          color="text-success"
        />
        <StatCard
          label="本月营收"
          value={`¥${monthRevenue.total.toFixed(2)}`}
          color="text-primary-600"
        />
        <StatCard
          label="库存总量"
          value={`${inventoryCount.total} 盆`}
          color="text-brown"
        />
        <StatCard
          label="待处理预约"
          value={`${pendingBookings.length} 条`}
          color="text-gold"
        />
      </div>

      {/* Trend Chart */}
      <div className="mb-8">
        <DashboardChart />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="font-semibold text-gray-700 mb-4">快捷操作</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <QuickLink href="/admin/purchase" label="录入进货" />
          <QuickLink href="/admin/sales" label="录入销售" />
          <QuickLink href="/admin/varieties" label="品种管理" />
          <QuickLink href="/admin/reports" label="查看报表" />
          <QuickLink href="/admin/content" label="发布内容" />
          <QuickLink href="/admin/videos" label="上传视频" />
          <QuickLink href="/admin/inventory" label="库存管理" />
          <QuickLink href="/admin/notes" label="写学习笔记" />
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

function QuickLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      className="block text-center py-3 px-4 bg-primary-50 text-primary-700 text-sm font-medium rounded-lg hover:bg-primary-100 transition-colors"
    >
      {label}
    </a>
  );
}
