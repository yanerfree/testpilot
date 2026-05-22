CREATE TABLE `about_page` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`content` text NOT NULL,
	`updatedAt` text DEFAULT (datetime('now'))
);
--> statement-breakpoint
CREATE TABLE `admin` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`username` text NOT NULL,
	`passwordHash` text NOT NULL,
	`createdAt` text DEFAULT (datetime('now'))
);
--> statement-breakpoint
CREATE UNIQUE INDEX `admin_username_unique` ON `admin` (`username`);--> statement-breakpoint
CREATE TABLE `article` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`title` text NOT NULL,
	`body` text NOT NULL,
	`category` text,
	`coverImage` text,
	`videoId` integer,
	`isPublished` integer DEFAULT 1,
	`createdAt` text DEFAULT (datetime('now')),
	`updatedAt` text DEFAULT (datetime('now')),
	FOREIGN KEY (`videoId`) REFERENCES `video`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `booking` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`customerName` text NOT NULL,
	`phone` text NOT NULL,
	`address` text,
	`requirement` text,
	`status` text DEFAULT 'pending',
	`createdAt` text DEFAULT (datetime('now'))
);
--> statement-breakpoint
CREATE TABLE `content` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`type` text NOT NULL,
	`title` text NOT NULL,
	`body` text,
	`images` text,
	`videoId` integer,
	`isPublished` integer DEFAULT 1,
	`createdAt` text DEFAULT (datetime('now')),
	`updatedAt` text DEFAULT (datetime('now')),
	FOREIGN KEY (`videoId`) REFERENCES `video`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `guestbook` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`nickname` text NOT NULL,
	`message` text NOT NULL,
	`adminReply` text,
	`isVisible` integer DEFAULT 1,
	`createdAt` text DEFAULT (datetime('now')),
	`repliedAt` text
);
--> statement-breakpoint
CREATE TABLE `inventory` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`varietyId` integer NOT NULL,
	`quantity` integer NOT NULL,
	`location` text,
	`condition` text NOT NULL,
	`category` text NOT NULL,
	`updatedAt` text DEFAULT (datetime('now')),
	FOREIGN KEY (`varietyId`) REFERENCES `variety`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE TABLE `note` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`title` text NOT NULL,
	`body` text NOT NULL,
	`tags` text,
	`noteDate` text NOT NULL,
	`createdAt` text DEFAULT (datetime('now')),
	`updatedAt` text DEFAULT (datetime('now'))
);
--> statement-breakpoint
CREATE TABLE `pricing_log` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`varietyId` integer NOT NULL,
	`mode` text NOT NULL,
	`manualPrice` real,
	`markupPercent` real,
	`calculatedPrice` real NOT NULL,
	`baseCost` real,
	`createdAt` text DEFAULT (datetime('now')),
	FOREIGN KEY (`varietyId`) REFERENCES `variety`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE TABLE `purchase` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`varietyId` integer NOT NULL,
	`quantity` integer NOT NULL,
	`unitPrice` real NOT NULL,
	`totalCost` real NOT NULL,
	`purchaseDate` text NOT NULL,
	`note` text,
	`createdAt` text DEFAULT (datetime('now')),
	FOREIGN KEY (`varietyId`) REFERENCES `variety`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE TABLE `sale` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`varietyId` integer NOT NULL,
	`quantity` integer NOT NULL,
	`unitSalePrice` real NOT NULL,
	`totalRevenue` real NOT NULL,
	`costBasis` real NOT NULL,
	`profit` real NOT NULL,
	`saleDate` text NOT NULL,
	`note` text,
	`createdAt` text DEFAULT (datetime('now')),
	FOREIGN KEY (`varietyId`) REFERENCES `variety`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE TABLE `service` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`name` text NOT NULL,
	`description` text,
	`price` text,
	`icon` text,
	`sortOrder` integer DEFAULT 0,
	`createdAt` text DEFAULT (datetime('now'))
);
--> statement-breakpoint
CREATE TABLE `shop_cost` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`name` text NOT NULL,
	`amount` real NOT NULL,
	`frequency` text NOT NULL,
	`category` text,
	`monthlyAmount` real NOT NULL,
	`createdAt` text DEFAULT (datetime('now'))
);
--> statement-breakpoint
CREATE TABLE `shop_revenue` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`optimistic` real NOT NULL,
	`moderate` real NOT NULL,
	`conservative` real NOT NULL,
	`initialInvestment` real,
	`updatedAt` text DEFAULT (datetime('now'))
);
--> statement-breakpoint
CREATE TABLE `variety` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`name` text NOT NULL,
	`appearance` text,
	`difficulty` text,
	`growthHabit` text,
	`suitableScene` text,
	`marketPrice` real,
	`popularityRating` integer,
	`seasonalIndex` text,
	`customerFeedback` text,
	`showInFrontend` integer DEFAULT 0,
	`frontendDescription` text,
	`coverImage` text,
	`createdAt` text DEFAULT (datetime('now')),
	`updatedAt` text DEFAULT (datetime('now'))
);
--> statement-breakpoint
CREATE TABLE `video` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`title` text NOT NULL,
	`description` text,
	`filePath` text NOT NULL,
	`thumbnailPath` text,
	`category` text,
	`duration` integer,
	`isPublic` integer DEFAULT 1,
	`createdAt` text DEFAULT (datetime('now')),
	`updatedAt` text DEFAULT (datetime('now'))
);
--> statement-breakpoint
CREATE TABLE `wastage` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`varietyId` integer NOT NULL,
	`quantity` integer NOT NULL,
	`reason` text NOT NULL,
	`costBasis` real NOT NULL,
	`totalLoss` real NOT NULL,
	`wastageDate` text NOT NULL,
	`note` text,
	`createdAt` text DEFAULT (datetime('now')),
	FOREIGN KEY (`varietyId`) REFERENCES `variety`(`id`) ON UPDATE no action ON DELETE cascade
);
