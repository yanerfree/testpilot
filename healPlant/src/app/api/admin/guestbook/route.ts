import { db } from "@/lib/db";
import { guestbook } from "@/lib/db/schema";
import { desc } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET() {
  const results = await db
    .select()
    .from(guestbook)
    .orderBy(desc(guestbook.createdAt))
    .limit(100);

  return NextResponse.json(results);
}
