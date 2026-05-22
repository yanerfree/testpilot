"use client";

import Link from "next/link";
import { useState } from "react";
import { Menu, X, Leaf } from "lucide-react";

const navItems = [
  { label: "首页", href: "/" },
  { label: "个人简介", href: "/about" },
  { label: "趣味广场", href: "/fun" },
  { label: "养护服务", href: "/services" },
  { label: "产品展示", href: "/products" },
  { label: "养花科普", href: "/knowledge" },
  { label: "互动留言", href: "/guestbook" },
];

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col bg-warm">
      <header className="bg-primary-700 text-white sticky top-0 z-50 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">
            <Leaf className="w-6 h-6" />
            HealPlant
          </Link>

          <nav className="hidden md:flex gap-6">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="text-sm hover:text-primary-200 transition-colors"
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <button
            className="md:hidden p-2"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {menuOpen && (
          <nav className="md:hidden bg-primary-800 border-t border-primary-600">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="block px-4 py-3 text-sm hover:bg-primary-700 transition-colors"
                onClick={() => setMenuOpen(false)}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        )}
      </header>

      <main className="flex-1">{children}</main>

      <footer className="bg-primary-800 text-white/80 py-8">
        <div className="max-w-6xl mx-auto px-4 text-center text-sm">
          <p className="mb-2">HealPlant · 绿植综合经营 · 武汉本地服务</p>
          <p className="text-white/50">© 2026 HealPlant. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
