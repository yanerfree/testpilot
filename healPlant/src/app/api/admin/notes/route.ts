import { db } from "@/lib/db";
import { note } from "@/lib/db/schema";
import { eq, desc, like } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const search = searchParams.get("search");
  const tag = searchParams.get("tag");

  let query = db.select().from(note).orderBy(desc(note.noteDate)).$dynamic();

  if (search) {
    query = query.where(like(note.title, `%${search}%`));
  }

  if (tag) {
    query = query.where(like(note.tags, `%${tag}%`));
  }

  const results = await query.limit(100);
  return NextResponse.json(results);
}

export async function POST(request: Request) {
  const body = await request.json();
  const result = await db.insert(note).values({
    title: body.title,
    body: body.body,
    tags: body.tags || null,
    noteDate: body.noteDate,
  }).returning();

  return NextResponse.json(result[0]);
}
