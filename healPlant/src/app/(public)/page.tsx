import Link from "next/link";
import { Leaf, Flower2, Scissors, BookOpen, MessageSquare, Video } from "lucide-react";

export default function HomePage() {
  return (
    <>
      {/* Hero Banner */}
      <section className="bg-gradient-to-br from-primary-600 to-primary-800 text-white py-20 md:py-32">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-white/20 rounded-full mb-6">
            <Leaf className="w-10 h-10" />
          </div>
          <h1 className="text-3xl md:text-5xl font-bold mb-4">
            每一片绿叶，都是生活的治愈
          </h1>
          <p className="text-lg md:text-xl text-white/80 mb-8 max-w-2xl mx-auto">
            专业绿植养护 · 花卉盆栽展示 · 养花知识分享 · 武汉本地服务
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/services"
              className="px-8 py-3 bg-white text-primary-700 font-semibold rounded-full hover:bg-primary-50 transition-colors"
            >
              查看养护服务
            </Link>
            <Link
              href="/fun"
              className="px-8 py-3 border-2 border-white/50 text-white font-semibold rounded-full hover:bg-white/10 transition-colors"
            >
              逛逛趣味广场
            </Link>
          </div>
        </div>
      </section>

      {/* Feature Cards */}
      <section className="max-w-6xl mx-auto px-4 -mt-12 relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <FeatureCard
            icon={<Scissors className="w-8 h-8 text-primary-600" />}
            title="上门养护服务"
            desc="浇水、修剪、换盆、除虫，专业上门绿植养护"
            href="/services"
          />
          <FeatureCard
            icon={<Video className="w-8 h-8 text-primary-600" />}
            title="趣味视频动态"
            desc="养护实操、生长记录、日常趣味短视频分享"
            href="/fun"
          />
          <FeatureCard
            icon={<Flower2 className="w-8 h-8 text-primary-600" />}
            title="花卉盆栽展示"
            desc="精选绿植实拍，习性介绍，供您挑选参考"
            href="/products"
          />
        </div>
      </section>

      {/* Sections */}
      <section className="max-w-6xl mx-auto px-4 py-16">
        <h2 className="text-2xl font-bold text-center text-primary-800 mb-2">
          探索更多
        </h2>
        <p className="text-center text-gray-500 mb-10">
          养花知识 · 趣味日常 · 互动交流
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <SectionCard
            icon={<BookOpen className="w-6 h-6" />}
            title="养花科普"
            desc="养护技巧、病虫害处理、新手入门指南"
            href="/knowledge"
            color="bg-primary-50 text-primary-600"
          />
          <SectionCard
            icon={<Leaf className="w-6 h-6" />}
            title="个人简介"
            desc="我的养花之路，技能成长历程"
            href="/about"
            color="bg-green-50 text-green-600"
          />
          <SectionCard
            icon={<MessageSquare className="w-6 h-6" />}
            title="互动留言"
            desc="交流养花心得，提问答疑"
            href="/guestbook"
            color="bg-amber-50 text-amber-600"
          />
          <SectionCard
            icon={<Flower2 className="w-6 h-6" />}
            title="产品展示"
            desc="可售绿植盆栽，实拍图片展示"
            href="/products"
            color="bg-pink-50 text-pink-600"
          />
        </div>
      </section>
    </>
  );
}

function FeatureCard({
  icon,
  title,
  desc,
  href,
}: {
  icon: React.ReactNode;
  title: string;
  desc: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="bg-white rounded-xl shadow-sm hover:shadow-md p-6 transition-shadow flex flex-col items-center text-center"
    >
      <div className="w-16 h-16 bg-primary-50 rounded-full flex items-center justify-center mb-4">
        {icon}
      </div>
      <h3 className="font-semibold text-lg text-gray-800 mb-2">{title}</h3>
      <p className="text-sm text-gray-500">{desc}</p>
    </Link>
  );
}

function SectionCard({
  icon,
  title,
  desc,
  href,
  color,
}: {
  icon: React.ReactNode;
  title: string;
  desc: string;
  href: string;
  color: string;
}) {
  return (
    <Link
      href={href}
      className="bg-white rounded-lg border border-gray-100 hover:border-primary-200 p-5 transition-colors group"
    >
      <div
        className={`w-10 h-10 rounded-lg flex items-center justify-center mb-3 ${color}`}
      >
        {icon}
      </div>
      <h3 className="font-medium text-gray-800 mb-1 group-hover:text-primary-600 transition-colors">
        {title}
      </h3>
      <p className="text-sm text-gray-500">{desc}</p>
    </Link>
  );
}
