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

export async function POST(request: Request) {
  const body = await request.json();
  const result = await db.insert(service).values({
    name: body.name,
    description: body.description || null,
    price: body.price || null,
    icon: body.icon || null,
    sortOrder: body.sortOrder || 0,
  }).returning();

  return NextResponse.json(result[0]);
}
