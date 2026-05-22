import { sqliteTable, text, integer, real } from "drizzle-orm/sqlite-core";
import { sql } from "drizzle-orm";

const timestamp = () =>
  text().default(sql`(datetime('now'))`);

export const admin = sqliteTable("admin", {
  id: integer().primaryKey({ autoIncrement: true }),
  username: text().notNull().unique(),
  passwordHash: text().notNull(),
  createdAt: timestamp(),
});

export const variety = sqliteTable("variety", {
  id: integer().primaryKey({ autoIncrement: true }),
  name: text().notNull(),
  appearance: text(),
  difficulty: text().$type<"easy" | "medium" | "hard">(),
  growthHabit: text(),
  suitableScene: text(),
  marketPrice: real(),
  popularityRating: integer(),
  seasonalIndex: text(),
  customerFeedback: text(),
  showInFrontend: integer().default(0),
  frontendDescription: text(),
  coverImage: text(),
  createdAt: timestamp(),
  updatedAt: timestamp(),
});

export const pricingLog = sqliteTable("pricing_log", {
  id: integer().primaryKey({ autoIncrement: true }),
  varietyId: integer()
    .notNull()
    .references(() => variety.id, { onDelete: "cascade" }),
  mode: text().$type<"manual" | "markup">().notNull(),
  manualPrice: real(),
  markupPercent: real(),
  calculatedPrice: real().notNull(),
  baseCost: real(),
  createdAt: timestamp(),
});

export const purchase = sqliteTable("purchase", {
  id: integer().primaryKey({ autoIncrement: true }),
  varietyId: integer()
    .notNull()
    .references(() => variety.id, { onDelete: "cascade" }),
  quantity: integer().notNull(),
  unitPrice: real().notNull(),
  totalCost: real().notNull(),
  purchaseDate: text().notNull(),
  note: text(),
  createdAt: timestamp(),
});

export const sale = sqliteTable("sale", {
  id: integer().primaryKey({ autoIncrement: true }),
  varietyId: integer()
    .notNull()
    .references(() => variety.id, { onDelete: "cascade" }),
  quantity: integer().notNull(),
  unitSalePrice: real().notNull(),
  totalRevenue: real().notNull(),
  costBasis: real().notNull(),
  profit: real().notNull(),
  saleDate: text().notNull(),
  note: text(),
  createdAt: timestamp(),
});

export const wastage = sqliteTable("wastage", {
  id: integer().primaryKey({ autoIncrement: true }),
  varietyId: integer()
    .notNull()
    .references(() => variety.id, { onDelete: "cascade" }),
  quantity: integer().notNull(),
  reason: text().$type<"wilt" | "damage" | "defect" | "other">().notNull(),
  costBasis: real().notNull(),
  totalLoss: real().notNull(),
  wastageDate: text().notNull(),
  note: text(),
  createdAt: timestamp(),
});

export const inventory = sqliteTable("inventory", {
  id: integer().primaryKey({ autoIncrement: true }),
  varietyId: integer()
    .notNull()
    .references(() => variety.id, { onDelete: "cascade" }),
  quantity: integer().notNull(),
  location: text(),
  condition: text().$type<"good" | "needs-care" | "pending">().notNull(),
  category: text().$type<"for-sale" | "for-care">().notNull(),
  updatedAt: timestamp(),
});

export const content = sqliteTable("content", {
  id: integer().primaryKey({ autoIncrement: true }),
  type: text()
    .$type<"plants" | "video" | "pets" | "quotes" | "essays">()
    .notNull(),
  title: text().notNull(),
  body: text(),
  images: text(),
  videoId: integer().references(() => video.id),
  isPublished: integer().default(1),
  createdAt: timestamp(),
  updatedAt: timestamp(),
});

export const video = sqliteTable("video", {
  id: integer().primaryKey({ autoIncrement: true }),
  title: text().notNull(),
  description: text(),
  filePath: text().notNull(),
  thumbnailPath: text(),
  category: text().$type<
    "care" | "timelapse" | "fun" | "pets" | "shop"
  >(),
  duration: integer(),
  isPublic: integer().default(1),
  createdAt: timestamp(),
  updatedAt: timestamp(),
});

export const article = sqliteTable("article", {
  id: integer().primaryKey({ autoIncrement: true }),
  title: text().notNull(),
  body: text().notNull(),
  category: text().$type<"tips" | "seasonal" | "pests" | "beginner">(),
  coverImage: text(),
  videoId: integer().references(() => video.id),
  isPublished: integer().default(1),
  createdAt: timestamp(),
  updatedAt: timestamp(),
});

export const service = sqliteTable("service", {
  id: integer().primaryKey({ autoIncrement: true }),
  name: text().notNull(),
  description: text(),
  price: text(),
  icon: text(),
  sortOrder: integer().default(0),
  createdAt: timestamp(),
});

export const booking = sqliteTable("booking", {
  id: integer().primaryKey({ autoIncrement: true }),
  customerName: text().notNull(),
  phone: text().notNull(),
  address: text(),
  requirement: text(),
  status: text()
    .$type<"pending" | "contacted" | "completed">()
    .default("pending"),
  createdAt: timestamp(),
});

export const guestbook = sqliteTable("guestbook", {
  id: integer().primaryKey({ autoIncrement: true }),
  nickname: text().notNull(),
  message: text().notNull(),
  adminReply: text(),
  isVisible: integer().default(1),
  createdAt: timestamp(),
  repliedAt: text(),
});

export const note = sqliteTable("note", {
  id: integer().primaryKey({ autoIncrement: true }),
  title: text().notNull(),
  body: text().notNull(),
  tags: text(),
  noteDate: text().notNull(),
  createdAt: timestamp(),
  updatedAt: timestamp(),
});

export const shopCost = sqliteTable("shop_cost", {
  id: integer().primaryKey({ autoIncrement: true }),
  name: text().notNull(),
  amount: real().notNull(),
  frequency: text().$type<"monthly" | "quarterly" | "yearly">().notNull(),
  category: text().$type<
    "rent" | "utility" | "labor" | "seedling" | "other"
  >(),
  monthlyAmount: real().notNull(),
  createdAt: timestamp(),
});

export const shopRevenue = sqliteTable("shop_revenue", {
  id: integer().primaryKey({ autoIncrement: true }),
  optimistic: real().notNull(),
  moderate: real().notNull(),
  conservative: real().notNull(),
  initialInvestment: real(),
  updatedAt: timestamp(),
});

export const aboutPage = sqliteTable("about_page", {
  id: integer().primaryKey({ autoIncrement: true }),
  content: text().notNull(),
  updatedAt: timestamp(),
});
