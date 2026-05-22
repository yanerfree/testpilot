import { db } from "@/lib/db";
import { article } from "@/lib/db/schema";
import { eq, desc } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const category = searchParams.get("category");

  let query = db.select().from(article).orderBy(desc(article.createdAt)).$dynamic();

  if (category) {
    query = query.where(eq(article.category, category as "tips" | "seasonal" | "pests" | "beginner"));
  }

  const results = await query.limit(100);
  return NextResponse.json(results);
}

export async function POST(request: Request) {
  const body = await request.json();
  const result = await db.insert(article).values({
    title: body.title,
    body: body.body,
    category: body.category || null,
    coverImage: body.coverImage || null,
    videoId: body.videoId || null,
    isPublished: body.isPublished ? 1 : 0,
  }).returning();

  return NextResponse.json(result[0]);
}
