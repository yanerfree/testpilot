import { db } from "@/lib/db";
import { variety } from "@/lib/db/schema";
import { desc, like, eq } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const search = searchParams.get("search");

  let query = db.select().from(variety).orderBy(desc(variety.createdAt)).$dynamic();

  if (search) {
    query = query.where(like(variety.name, `%${search}%`));
  }

  const results = await query.limit(100);
  return NextResponse.json(results);
}

export async function POST(request: Request) {
  const body = await request.json();
  const result = await db.insert(variety).values({
    name: body.name,
    appearance: body.appearance || null,
    difficulty: body.difficulty || null,
    growthHabit: body.growthHabit || null,
    suitableScene: body.suitableScene || null,
    marketPrice: body.marketPrice || null,
    popularityRating: body.popularityRating || null,
    seasonalIndex: body.seasonalIndex ? JSON.stringify(body.seasonalIndex) : null,
    customerFeedback: body.customerFeedback || null,
    showInFrontend: body.showInFrontend ? 1 : 0,
    frontendDescription: body.frontendDescription || null,
    coverImage: body.coverImage || null,
  }).returning();

  return NextResponse.json(result[0]);
}
