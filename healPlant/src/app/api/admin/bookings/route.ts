import { db } from "@/lib/db";
import { booking } from "@/lib/db/schema";
import { desc } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET() {
  const results = await db
    .select()
    .from(booking)
    .orderBy(desc(booking.createdAt))
    .limit(100);

  return NextResponse.json(results);
}
