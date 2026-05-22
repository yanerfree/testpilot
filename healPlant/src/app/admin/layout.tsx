"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { signOut } from "next-auth/react";
import {
  LayoutDashboard,
  FileText,
  Flower2,
  ShoppingCart,
  TrendingDown,
  BarChart3,
  Store,
  Package,
  Video,
  BookOpen,
  Calendar,
  MessageSquare,
  Scissors,
  Info,
  Menu,
  X,
  LogOut,
  Leaf,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navGroups = [
  {
    label: "总览",
    items: [
      { label: "仪表盘", href: "/admin", icon: LayoutDashboard },
    ],
  },
  {
    label: "内容管理",
    items: [
      { label: "个人简介", href: "/admin/about", icon: Info },
      { label: "趣味内容", href: "/admin/content", icon: FileText },
      { label: "科普文章", href: "/admin/articles", icon: BookOpen },
      { label: "产品展示", href: "/admin/products-display", icon: Flower2 },
      { label: "服务项目", href: "/admin/services", icon: Scissors },
      { label: "留言管理", href: "/admin/guestbook", icon: MessageSquare },
    ],
  },
  {
    label: "经营管理",
    items: [
      { label: "品种资料库", href: "/admin/varieties", icon: Flower2 },
      { label: "进货台账", href: "/admin/purchase", icon: ShoppingCart },
      { label: "销售台账", href: "/admin/sales", icon: TrendingDown },
      { label: "损耗登记", href: "/admin/wastage", icon: TrendingDown },
      { label: "经营报表", href: "/admin/reports", icon: BarChart3 },
      { label: "小店测算", href: "/admin/shop-calc", icon: Store },
      { label: "库存管理", href: "/admin/inventory", icon: Package },
    ],
  },
  {
    label: "其他",
    items: [
      { label: "视频管理", href: "/admin/videos", icon: Video },
      { label: "学习台账", href: "/admin/notes", icon: BookOpen },
      { label: "预约管理", href: "/admin/bookings", icon: Calendar },
    ],
  },
];

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const toggleGroup = (label: string) => {
    setCollapsed((prev) => ({ ...prev, [label]: !prev[label] }));
  };

  const sidebar = (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-primary-100">
        <Link href="/admin" className="flex items-center gap-2 font-bold text-primary-700">
          <Leaf className="w-5 h-5" />
          HealPlant 后台
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto py-2">
        {navGroups.map((group) => (
          <div key={group.label} className="mb-1">
            <button
              onClick={() => toggleGroup(group.label)}
              className="w-full flex items-center justify-between px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider hover:text-gray-700"
            >
              {group.label}
              {collapsed[group.label] ? (
                <ChevronRight className="w-3 h-3" />
              ) : (
                <ChevronDown className="w-3 h-3" />
              )}
            </button>
            {!collapsed[group.label] &&
              group.items.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setSidebarOpen(false)}
                    className={cn(
                      "flex items-center gap-3 px-4 py-2.5 text-sm transition-colors mx-2 rounded-md",
                      isActive
                        ? "bg-primary-100 text-primary-700 font-medium"
                        : "text-gray-600 hover:bg-primary-50 hover:text-primary-600"
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    {item.label}
                  </Link>
                );
              })}
          </div>
        ))}
      </nav>

      <div className="p-4 border-t border-primary-100">
        <button
          onClick={() => signOut({ callbackUrl: "/" })}
          className="flex items-center gap-2 text-sm text-gray-500 hover:text-danger transition-colors w-full"
        >
          <LogOut className="w-4 h-4" />
          退出登录
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-60 bg-white border-r border-gray-200 flex-col fixed h-full">
        {sidebar}
      </aside>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 z-40">
          <div
            className="absolute inset-0 bg-black/30"
            onClick={() => setSidebarOpen(false)}
          />
          <aside className="relative w-64 bg-white h-full shadow-lg">
            {sidebar}
          </aside>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 lg:ml-60">
        <header className="bg-white border-b border-gray-200 h-14 flex items-center px-4 sticky top-0 z-30">
          <button
            className="lg:hidden mr-3 p-1"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="w-5 h-5 text-gray-600" />
          </button>
          <div className="flex-1" />
          <Link
            href="/"
            className="text-sm text-primary-600 hover:text-primary-700"
            target="_blank"
          >
            查看前台 →
          </Link>
        </header>

        <main className="p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
