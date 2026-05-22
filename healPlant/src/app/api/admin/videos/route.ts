import { db } from "@/lib/db";
import { video } from "@/lib/db/schema";
import { desc } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET() {
  const results = await db
    .select()
    .from(video)
    .orderBy(desc(video.createdAt));

  return NextResponse.json(results);
}

export async function POST(request: Request) {
  const body = await request.json();
  const result = await db.insert(video).values({
    title: body.title,
    description: body.description || null,
    filePath: body.filePath,
    thumbnailPath: body.thumbnailPath || null,
    category: body.category || null,
    duration: body.duration || null,
    isPublic: body.isPublic ? 1 : 0,
  }).returning();

  return NextResponse.json(result[0]);
}
