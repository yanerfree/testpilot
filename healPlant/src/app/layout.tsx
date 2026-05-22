import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HealPlant - 绿植综合经营",
  description: "专业绿植养护服务 · 花卉盆栽展示 · 养花知识科普",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
