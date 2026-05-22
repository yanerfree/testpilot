---
stepsCompleted: [init, discovery, tech-stack, data-model, api-design, security, deployment, complete]
inputDocuments: [brief.md, prd.md, ux-design.md]
workflowType: architecture
project_name: HealPlant
user_name: Dreamer
date: 2026-05-22
---

# Architecture Decision Document: HealPlant

## 1. 项目概述

**类型：** 全栈 Web 应用（Full Stack Web Application）
**复杂度：** 中等（双角色权限、CRUD 数据管理、文件上传、数据报表）
**部署模型：** 单体应用，前后端分离

## 2. 技术选型

### 2.1 技术栈决策

| 层级 | 选型 | 理由 |
|------|------|------|
| **前端框架** | Next.js 14 (App Router) | SSR/SSG 混合渲染，前台页面 SEO 友好；React 生态成熟，组件库丰富 |
| **UI 组件库** | Tailwind CSS + shadcn/ui | Tailwind 实用优先，高度可定制；shadcn/ui 提供无样式组件基础，适合定制园艺风格 |
| **图表库** | Recharts | React 原生图表库，API 简洁，满足报表可视化需求 |
| **富文本编辑器** | Tiptap | 轻量、可扩展、支持图片嵌入，适合内容管理场景 |
| **后端运行时** | Next.js API Routes (Route Handlers) | 与前端统一部署，减少运维复杂度 |
| **数据库** | SQLite (via Drizzle ORM) | 单用户场景无需复杂数据库；SQLite 零配置、文件级部署、备份简单 |
| **ORM** | Drizzle ORM | 类型安全、轻量、支持 SQLite、迁移方便 |
| **认证** | NextAuth.js (Auth.js v5) | 成熟的 Next.js 认证方案，支持 Credentials Provider（账号密码） |
| **文件存储** | 本地文件系统 + public 目录 | V1 简单方案，单服务器部署；V2 可迁移至 OSS |
| **视频播放** | HTML5 Video + react-player | 原生播放器满足基本需求，react-player 提供更好的控制 UI |
| **包管理器** | pnpm | 快速、节省磁盘空间 |
| **语言** | TypeScript | 全栈类型安全 |

### 2.2 关键架构决策

**ADR-1: 单体全栈 vs 前后端分离微服务**
- **决策：** 采用 Next.js 单体全栈应用
- **理由：** 单管理员、中等复杂度、部署简单优先。微服务增加不必要的运维成本
- **影响：** 前端和 API 共享同一 Next.js 进程，统一部署

**ADR-2: SQLite vs PostgreSQL**
- **决策：** 采用 SQLite
- **理由：** 单用户场景无并发写入压力；零配置部署；文件级备份（cp 即可）；Drizzle ORM 抽象数据库层，未来可迁移
- **影响：** 不支持高并发写入，但符合单管理员使用场景

**ADR-3: 本地文件存储 vs 云 OSS**
- **决策：** V1 使用本地文件存储
- **理由：** 降低启动成本，避免云服务依赖。上传文件存放在 `/uploads/` 目录
- **影响：** 单服务器限制，备份需包含上传目录。V2 可插件化迁移到 OSS

**ADR-4: 服务端渲染策略**
- **决策：** 前台页面 SSG/ISR，后台页面 CSR
- **理由：** 前台内容页适合静态生成提升加载速度；后台管理页面交互密集适合客户端渲染
- **影响：** 前台内容更新需触发重新生成或使用 ISR

---

## 3. 系统架构

### 3.1 高层架构

```
┌─────────────────────────────────────────┐
│                浏览器                     │
│   前台页面 (SSG/ISR)  │  后台页面 (CSR)   │
└──────────┬────────────┴──────┬──────────┘
           │                   │
┌──────────▼───────────────────▼──────────┐
│            Next.js App Router            │
│  ┌──────────────┐  ┌──────────────────┐ │
│  │  Pages/Layout │  │  API Route       │ │
│  │  (前台 SSG)   │  │  Handlers        │ │
│  │  (后台 CSR)   │  │  (/api/*)        │ │
│  └──────────────┘  └───────┬──────────┘ │
│                            │            │
│  ┌─────────────────────────▼──────────┐ │
│  │         Service Layer              │ │
│  │  (Business Logic + Validation)     │ │
│  └─────────────┬──────────────────────┘ │
│                │                        │
│  ┌─────────────▼──────────────────────┐ │
│  │      Drizzle ORM + SQLite          │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │      File Storage (/uploads/)      │ │
│  └────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

### 3.2 目录结构

```
healPlant/
├── src/
│   ├── app/                      # Next.js App Router
│   │   ├── (public)/             # 前台路由组
│   │   │   ├── page.tsx          # 首页
│   │   │   ├── about/
│   │   │   ├── fun/
│   │   │   ├── services/
│   │   │   ├── products/
│   │   │   ├── knowledge/
│   │   │   ├── guestbook/
│   │   │   └── layout.tsx        # 前台布局
│   │   ├── (auth)/               # 认证路由组
│   │   │   └── login/
│   │   ├── admin/                # 后台路由 (需鉴权)
│   │   │   ├── page.tsx          # Dashboard
│   │   │   ├── content/          # 内容管理
│   │   │   ├── varieties/        # 品种资料库
│   │   │   ├── purchase/         # 进货台账
│   │   │   ├── sales/            # 销售台账
│   │   │   ├── wastage/          # 损耗登记
│   │   │   ├── reports/          # 经营报表
│   │   │   ├── shop-calc/        # 小店测算
│   │   │   ├── inventory/        # 库存管理
│   │   │   ├── videos/           # 视频管理
│   │   │   ├── notes/            # 学习台账
│   │   │   ├── bookings/         # 预约管理
│   │   │   └── layout.tsx        # 后台布局
│   │   ├── api/                  # API Route Handlers
│   │   │   ├── auth/
│   │   │   ├── content/
│   │   │   ├── varieties/
│   │   │   ├── purchase/
│   │   │   ├── sales/
│   │   │   ├── wastage/
│   │   │   ├── reports/
│   │   │   ├── shop-calc/
│   │   │   ├── inventory/
│   │   │   ├── videos/
│   │   │   ├── notes/
│   │   │   ├── bookings/
│   │   │   ├── guestbook/
│   │   │   └── upload/
│   │   ├── layout.tsx            # Root Layout
│   │   └── globals.css
│   ├── components/
│   │   ├── ui/                   # shadcn/ui 基础组件
│   │   ├── public/               # 前台专用组件
│   │   ├── admin/                # 后台专用组件
│   │   └── shared/               # 公共组件
│   ├── lib/
│   │   ├── db/
│   │   │   ├── schema.ts         # Drizzle Schema
│   │   │   ├── index.ts          # DB 连接
│   │   │   └── migrations/
│   │   ├── auth.ts               # NextAuth 配置
│   │   ├── upload.ts             # 文件上传工具
│   │   └── utils.ts              # 通用工具函数
│   ├── services/                 # 业务逻辑层
│   │   ├── variety.service.ts
│   │   ├── purchase.service.ts
│   │   ├── sales.service.ts
│   │   ├── wastage.service.ts
│   │   ├── report.service.ts
│   │   ├── inventory.service.ts
│   │   └── pricing.service.ts
│   └── types/                    # TypeScript 类型定义
├── public/                       # 静态资源
├── uploads/                      # 用户上传文件
│   ├── images/
│   └── videos/
├── drizzle.config.ts
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── package.json
└── .env.local
```

---

## 4. 数据模型

### 4.1 ER 关系图

```
┌──────────────┐     ┌──────────────┐
│    Admin      │     │   Variety    │
│ (管理员账号)   │     │  (品种)      │
└──────────────┘     └──────┬───────┘
                            │ 1
                     ┌──────┼──────────────┐
                     │      │              │
                    ▼ N    ▼ N           ▼ N
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ Purchase │ │   Sale   │ │ Wastage  │
              │ (进货)   │ │  (销售)  │ │  (损耗)  │
              └──────────┘ └──────────┘ └──────────┘
                                               
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Inventory   │  │ PricingLog   │  │   Content    │
│  (库存)      │  │ (定价历史)    │  │  (内容)      │
└──────────────┘  └──────────────┘  └──────────────┘

┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Video      │  │   Article    │  │   Booking    │
│  (视频)      │  │ (科普文章)    │  │  (预约)      │
└──────────────┘  └──────────────┘  └──────────────┘

┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Guestbook   │  │    Note      │  │  ShopCost    │
│  (留言)      │  │ (学习笔记)    │  │ (小店成本项) │
└──────────────┘  └──────────────┘  └──────────────┘

┌──────────────┐  ┌──────────────┐
│   Service    │  │  AboutPage   │
│ (服务项目)    │  │ (简介内容)    │
└──────────────┘  └──────────────┘
```

### 4.2 核心表定义

```typescript
// --- 管理员 ---
admin {
  id: integer PK autoincrement
  username: text NOT NULL UNIQUE
  passwordHash: text NOT NULL
  createdAt: timestamp DEFAULT now
}

// --- 品种资料库 ---
variety {
  id: integer PK autoincrement
  name: text NOT NULL
  appearance: text           // 外形特征
  difficulty: text           // easy/medium/hard
  growthHabit: text          // 生长习性
  suitableScene: text        // 适用场景
  marketPrice: real          // 市场进价
  popularityRating: integer  // 热度等级 1-5
  seasonalIndex: text        // JSON: ["spring","summer"]
  customerFeedback: text     // 顾客反馈
  showInFrontend: integer DEFAULT 0  // 前台是否展示
  frontendDescription: text  // 前台公开描述
  coverImage: text           // 封面图路径
  createdAt: timestamp
  updatedAt: timestamp
}

// --- 定价历史 ---
pricingLog {
  id: integer PK autoincrement
  varietyId: integer FK → variety.id
  mode: text NOT NULL        // "manual" | "markup"
  manualPrice: real          // 手动售价
  markupPercent: real        // 涨幅百分比
  calculatedPrice: real NOT NULL  // 最终计算售价
  baseCost: real             // 计算时的进价基准
  createdAt: timestamp
}

// --- 进货台账 ---
purchase {
  id: integer PK autoincrement
  varietyId: integer FK → variety.id
  quantity: integer NOT NULL
  unitPrice: real NOT NULL
  totalCost: real NOT NULL   // = quantity * unitPrice
  purchaseDate: text NOT NULL  // YYYY-MM-DD
  note: text
  createdAt: timestamp
}

// --- 销售台账 ---
sale {
  id: integer PK autoincrement
  varietyId: integer FK → variety.id
  quantity: integer NOT NULL
  unitSalePrice: real NOT NULL
  totalRevenue: real NOT NULL  // = quantity * unitSalePrice
  costBasis: real NOT NULL     // 该品种最近进价
  profit: real NOT NULL        // = totalRevenue - costBasis * quantity
  saleDate: text NOT NULL
  note: text
  createdAt: timestamp
}

// --- 损耗登记 ---
wastage {
  id: integer PK autoincrement
  varietyId: integer FK → variety.id
  quantity: integer NOT NULL
  reason: text NOT NULL        // wilt/damage/defect/other
  costBasis: real NOT NULL     // 该品种最近进价
  totalLoss: real NOT NULL     // = quantity * costBasis
  wastageDate: text NOT NULL
  note: text
  createdAt: timestamp
}

// --- 库存 ---
inventory {
  id: integer PK autoincrement
  varietyId: integer FK → variety.id
  quantity: integer NOT NULL
  location: text               // 摆放位置
  condition: text NOT NULL     // good/needs-care/pending
  category: text NOT NULL      // for-sale/for-care
  updatedAt: timestamp
}

// --- 趣味内容 ---
content {
  id: integer PK autoincrement
  type: text NOT NULL          // plants/video/pets/quotes/essays
  title: text NOT NULL
  body: text                   // 富文本内容
  images: text                 // JSON array of image paths
  videoId: integer FK → video.id  // 关联视频
  isPublished: integer DEFAULT 1
  createdAt: timestamp
  updatedAt: timestamp
}

// --- 视频 ---
video {
  id: integer PK autoincrement
  title: text NOT NULL
  description: text
  filePath: text NOT NULL
  thumbnailPath: text
  category: text               // care/timelapse/fun/pets/shop
  duration: integer            // 秒
  isPublic: integer DEFAULT 1
  createdAt: timestamp
  updatedAt: timestamp
}

// --- 科普文章 ---
article {
  id: integer PK autoincrement
  title: text NOT NULL
  body: text NOT NULL          // 富文本
  category: text               // tips/seasonal/pests/beginner
  coverImage: text
  videoId: integer FK → video.id
  isPublished: integer DEFAULT 1
  createdAt: timestamp
  updatedAt: timestamp
}

// --- 服务项目 ---
service {
  id: integer PK autoincrement
  name: text NOT NULL
  description: text
  price: text                  // 收费说明
  icon: text                   // 图标名称
  sortOrder: integer DEFAULT 0
  createdAt: timestamp
}

// --- 预约 ---
booking {
  id: integer PK autoincrement
  customerName: text NOT NULL
  phone: text NOT NULL
  address: text
  requirement: text
  status: text DEFAULT 'pending'  // pending/contacted/completed
  createdAt: timestamp
}

// --- 留言 ---
guestbook {
  id: integer PK autoincrement
  nickname: text NOT NULL
  message: text NOT NULL
  adminReply: text
  isVisible: integer DEFAULT 1
  createdAt: timestamp
  repliedAt: timestamp
}

// --- 学习笔记 ---
note {
  id: integer PK autoincrement
  title: text NOT NULL
  body: text NOT NULL
  tags: text                   // JSON array
  noteDate: text NOT NULL
  createdAt: timestamp
  updatedAt: timestamp
}

// --- 小店成本项 ---
shopCost {
  id: integer PK autoincrement
  name: text NOT NULL
  amount: real NOT NULL
  frequency: text NOT NULL     // monthly/quarterly/yearly
  category: text               // rent/utility/labor/seedling/other
  monthlyAmount: real NOT NULL // 折算月均
  createdAt: timestamp
}

// --- 小店营收预估 ---
shopRevenue {
  id: integer PK autoincrement
  optimistic: real NOT NULL    // 乐观预估
  moderate: real NOT NULL      // 中性预估
  conservative: real NOT NULL  // 保守预估
  initialInvestment: real      // 初始投入
  updatedAt: timestamp
}

// --- 个人简介 ---
aboutPage {
  id: integer PK autoincrement
  content: text NOT NULL       // 富文本
  updatedAt: timestamp
}
```

---

## 5. API 设计

### 5.1 API 路由总览

所有后台 API 路径以 `/api/admin/` 开头，需 JWT 鉴权。
前台公开 API 以 `/api/public/` 开头，无需鉴权。

**认证：**
```
POST /api/auth/login          # 登录
POST /api/auth/logout         # 登出
GET  /api/auth/session        # 检查登录状态
```

**前台公开 API：**
```
GET /api/public/about                  # 个人简介
GET /api/public/content?type=&page=    # 趣味内容列表
GET /api/public/content/:id            # 内容详情
GET /api/public/videos?category=&page= # 公开视频列表
GET /api/public/products?category=     # 前台产品列表
GET /api/public/products/:id           # 产品详情
GET /api/public/articles?category=     # 科普文章列表
GET /api/public/articles/:id           # 文章详情
GET /api/public/services               # 服务项目列表
GET /api/public/guestbook?page=        # 留言列表
POST /api/public/guestbook             # 提交留言
POST /api/public/bookings              # 提交预约
```

**后台管理 API：**
```
# 内容管理
PUT    /api/admin/about                   # 更新简介
GET    /api/admin/content?type=&page=     # 内容列表
POST   /api/admin/content                 # 新增内容
PUT    /api/admin/content/:id             # 编辑内容
DELETE /api/admin/content/:id             # 删除内容

# 品种资料库
GET    /api/admin/varieties?search=&filter= # 品种列表
POST   /api/admin/varieties               # 新增品种
GET    /api/admin/varieties/:id           # 品种详情
PUT    /api/admin/varieties/:id           # 编辑品种
DELETE /api/admin/varieties/:id           # 删除品种

# 定价
POST   /api/admin/varieties/:id/pricing   # 新增定价记录
GET    /api/admin/varieties/:id/pricing   # 定价历史

# 进货
GET    /api/admin/purchase?dateFrom=&dateTo= # 进货列表
POST   /api/admin/purchase                # 新增进货
PUT    /api/admin/purchase/:id            # 编辑进货
DELETE /api/admin/purchase/:id            # 删除进货

# 销售
GET    /api/admin/sales?dateFrom=&dateTo= # 销售列表
POST   /api/admin/sales                   # 新增销售
PUT    /api/admin/sales/:id               # 编辑销售
DELETE /api/admin/sales/:id               # 删除销售

# 损耗
GET    /api/admin/wastage?dateFrom=&dateTo= # 损耗列表
POST   /api/admin/wastage                 # 新增损耗
PUT    /api/admin/wastage/:id             # 编辑损耗
DELETE /api/admin/wastage/:id             # 删除损耗

# 报表
GET    /api/admin/reports/summary?dateFrom=&dateTo= # 核算摘要
GET    /api/admin/reports/trend?period=              # 趋势数据
GET    /api/admin/reports/variety-ranking?dateFrom=&dateTo= # 品种排行

# 小店测算
GET    /api/admin/shop-calc              # 获取所有成本项和营收
POST   /api/admin/shop-calc/cost         # 新增成本项
PUT    /api/admin/shop-calc/cost/:id     # 编辑成本项
DELETE /api/admin/shop-calc/cost/:id     # 删除成本项
PUT    /api/admin/shop-calc/revenue      # 更新营收预估

# 库存
GET    /api/admin/inventory?status=&category= # 库存列表
POST   /api/admin/inventory              # 新增库存
PUT    /api/admin/inventory/:id          # 编辑库存
DELETE /api/admin/inventory/:id          # 删除库存

# 视频
GET    /api/admin/videos?category=       # 视频列表
POST   /api/admin/videos                 # 上传视频
PUT    /api/admin/videos/:id             # 编辑视频信息
DELETE /api/admin/videos/:id             # 删除视频

# 科普文章
GET    /api/admin/articles               # 文章列表
POST   /api/admin/articles               # 新增文章
PUT    /api/admin/articles/:id           # 编辑文章
DELETE /api/admin/articles/:id           # 删除文章

# 服务
GET    /api/admin/services               # 服务列表
POST   /api/admin/services               # 新增服务
PUT    /api/admin/services/:id           # 编辑服务
DELETE /api/admin/services/:id           # 删除服务

# 留言
GET    /api/admin/guestbook              # 留言列表（含未审核）
PUT    /api/admin/guestbook/:id/reply    # 回复留言
DELETE /api/admin/guestbook/:id          # 删除留言

# 预约
GET    /api/admin/bookings               # 预约列表
PUT    /api/admin/bookings/:id/status    # 更新预约状态

# 学习笔记
GET    /api/admin/notes?tag=&search=     # 笔记列表
POST   /api/admin/notes                  # 新增笔记
PUT    /api/admin/notes/:id              # 编辑笔记
DELETE /api/admin/notes/:id              # 删除笔记

# 文件上传
POST   /api/admin/upload/image           # 上传图片
POST   /api/admin/upload/video           # 上传视频
```

---

## 6. 安全架构

### 6.1 认证
- NextAuth.js Credentials Provider
- JWT Token 存储在 httpOnly Secure cookie
- Token 有效期 7 天，支持续期

### 6.2 授权
- 后台 API Middleware 统一校验 JWT
- Next.js Middleware 拦截 `/admin/*` 路由
- 前台 API 不含任何敏感数据字段

### 6.3 数据安全
- 密码使用 bcrypt (cost factor 12) 加盐哈希
- API 输入全部使用 Zod 校验
- 防 XSS：React 默认转义 + 富文本内容白名单过滤
- 防 CSRF：SameSite Cookie + Origin 校验
- 文件上传：类型白名单 + 大小限制 + 随机文件名

### 6.4 前后台隔离
- 前台 API `/api/public/*` 返回的品种数据不含 marketPrice 等字段
- 数据查询层使用 select 白名单，非全字段返回
- 后台路由 Next.js Middleware 层面拦截，不仅依赖前端判断

---

## 7. 部署架构

### 7.1 V1 部署方案

```
┌─────────────────────────┐
│     VPS / 云服务器        │
│  ┌───────────────────┐  │
│  │    Node.js         │  │
│  │    Next.js App     │  │
│  │    (PM2 管理)      │  │
│  └─────────┬─────────┘  │
│            │             │
│  ┌─────────▼─────────┐  │
│  │    SQLite DB       │  │
│  │  (data/healplant.db)│  │
│  └───────────────────┘  │
│                          │
│  ┌───────────────────┐  │
│  │  /uploads/         │  │
│  │  (图片+视频)       │  │
│  └───────────────────┘  │
│                          │
│  ┌───────────────────┐  │
│  │    Nginx           │  │
│  │  (反向代理+SSL)    │  │
│  └───────────────────┘  │
└─────────────────────────┘
```

### 7.2 环境变量

```env
DATABASE_URL=file:./data/healplant.db
NEXTAUTH_SECRET=<随机密钥>
NEXTAUTH_URL=https://your-domain.com
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=<bcrypt hash>
UPLOAD_DIR=./uploads
MAX_IMAGE_SIZE=10485760    # 10MB
MAX_VIDEO_SIZE=524288000   # 500MB
```

### 7.3 备份策略
- SQLite DB 文件每日备份（cron + cp）
- uploads 目录同步备份
- 保留最近 7 天备份

---

## 8. 性能策略

- 前台静态页面 ISR（增量静态再生），revalidate = 60s
- 图片上传自动压缩，生成 WebP 缩略图
- 视频支持 range request，实现边下载边播放
- 后台列表分页，每页 20 条
- 数据库查询建索引（varietyId, date 字段）
- Tailwind CSS purge 减小 CSS 体积

---

## 9. 未来扩展路径

| 阶段 | 扩展项 | 架构影响 |
|------|--------|----------|
| V2 | 云 OSS 文件存储 | 替换 upload.ts 为 OSS SDK，Drizzle schema 不变 |
| V2 | PostgreSQL | Drizzle ORM 切换 driver，schema 不变 |
| V2 | 微信小程序 | API 层不变，新增小程序前端 |
| V3 | 多角色权限 | 扩展 admin 表，增加 role 字段和权限矩阵 |
| V3 | 在线支付 | 接入微信支付/支付宝 SDK |
