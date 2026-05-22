import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import { hashSync } from "bcryptjs";
import { admin, aboutPage, service } from "./schema";
import path from "path";
import fs from "fs";

const dbDir = path.join(process.cwd(), "data");
if (!fs.existsSync(dbDir)) fs.mkdirSync(dbDir, { recursive: true });

const dbPath = path.join(dbDir, "healplant.db");
const sqlite = new Database(dbPath);
sqlite.pragma("journal_mode = WAL");
sqlite.pragma("foreign_keys = ON");

const db = drizzle(sqlite);

const username = process.env.ADMIN_USERNAME || "admin";
const password = process.env.ADMIN_PASSWORD || "admin123";
const passwordHash = hashSync(password, 12);

const existing = sqlite
  .prepare("SELECT id FROM admin WHERE username = ?")
  .get(username) as { id: number } | undefined;

if (!existing) {
  db.insert(admin).values({ username, passwordHash }).run();
  console.log(`Admin user "${username}" created.`);
} else {
  console.log(`Admin user "${username}" already exists.`);
}

const aboutExists = sqlite
  .prepare("SELECT id FROM about_page LIMIT 1")
  .get() as { id: number } | undefined;

if (!aboutExists) {
  db.insert(aboutPage)
    .values({
      content:
        "<h2>你好，我是一位绿植爱好者</h2><p>正在武汉学习绿植养护技术，热爱每一片绿叶带来的治愈力量。</p>",
    })
    .run();
  console.log("Default about page created.");
}

const servicesExist = sqlite
  .prepare("SELECT id FROM service LIMIT 1")
  .get() as { id: number } | undefined;

if (!servicesExist) {
  const defaultServices = [
    {
      name: "浇水养护",
      description: "专业浇水频率评估，根据植物习性和季节制定浇水方案",
      price: "单次 ¥30 起",
      icon: "droplets",
      sortOrder: 1,
    },
    {
      name: "修剪整形",
      description: "去除枯枝黄叶，修剪造型，促进健康生长",
      price: "单次 ¥50 起",
      icon: "scissors",
      sortOrder: 2,
    },
    {
      name: "换盆换土",
      description: "根据植株生长状况更换合适花盆和营养土",
      price: "单次 ¥80 起",
      icon: "flower2",
      sortOrder: 3,
    },
    {
      name: "除虫防害",
      description: "检查并处理常见虫害，预防病虫滋生",
      price: "单次 ¥60 起",
      icon: "bug",
      sortOrder: 4,
    },
    {
      name: "病害治理",
      description: "诊断植物病害并制定治疗方案，恢复植株健康",
      price: "单次 ¥100 起",
      icon: "heart-pulse",
      sortOrder: 5,
    },
  ];
  for (const s of defaultServices) {
    db.insert(service).values(s).run();
  }
  console.log("Default services created.");
}

sqlite.close();
console.log("Seed complete.");
