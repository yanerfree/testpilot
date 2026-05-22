import { db } from "@/lib/db";
import { content } from "@/lib/db/schema";
import { eq, desc } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get("type");

  let query = db.select().from(content).orderBy(desc(content.createdAt)).$dynamic();

  if (type) {
    query = query.where(eq(content.type, type as "plants" | "video" | "pets" | "quotes" | "essays"));
  }

  const results = await query.limit(100);
  return NextResponse.json(results);
}

export async function POST(request: Request) {
  const body = await request.json();
  const result = await db.insert(content).values({
    type: body.type,
    title: body.title,
    body: body.body || null,
    images: body.images || null,
    videoId: body.videoId || null,
    isPublished: body.isPublished ? 1 : 0,
  }).returning();

  return NextResponse.json(result[0]);
}
