import { db } from "@/lib/db";
import { content } from "@/lib/db/schema";
import { eq, desc, and } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get("type");
  const page = parseInt(searchParams.get("page") || "1");
  const pageSize = 20;
  const offset = (page - 1) * pageSize;

  const conditions = [eq(content.isPublished, 1)];

  if (type) {
    conditions.push(eq(content.type, type as "plants" | "video" | "pets" | "quotes" | "essays"));
  }

  const results = await db
    .select()
    .from(content)
    .where(and(...conditions))
    .orderBy(desc(content.createdAt))
    .limit(pageSize)
    .offset(offset);

  return NextResponse.json(results);
}
