import { db } from "@/lib/db";
import { variety } from "@/lib/db/schema";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET() {
  const results = await db
    .select({
      id: variety.id,
      name: variety.name,
      frontendDescription: variety.frontendDescription,
      coverImage: variety.coverImage,
      difficulty: variety.difficulty,
      growthHabit: variety.growthHabit,
      suitableScene: variety.suitableScene,
    })
    .from(variety)
    .where(eq(variety.showInFrontend, 1));

  return NextResponse.json(results);
}
