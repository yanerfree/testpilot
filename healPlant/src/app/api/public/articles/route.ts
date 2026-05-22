import { db } from "@/lib/db";
import { article } from "@/lib/db/schema";
import { eq, desc, and } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const category = searchParams.get("category");

  const conditions = [eq(article.isPublished, 1)];

  if (category) {
    conditions.push(eq(article.category, category as "tips" | "seasonal" | "pests" | "beginner"));
  }

  const results = await db
    .select()
    .from(article)
    .where(and(...conditions))
    .orderBy(desc(article.createdAt))
    .limit(100);

  return NextResponse.json(results);
}
