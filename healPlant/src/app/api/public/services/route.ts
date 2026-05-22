import { db } from "@/lib/db";
import { service } from "@/lib/db/schema";
import { asc } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET() {
  const results = await db
    .select()
    .from(service)
    .orderBy(asc(service.sortOrder));

  return NextResponse.json(results);
}
