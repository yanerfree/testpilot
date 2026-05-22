import { db } from "@/lib/db";
import { variety } from "@/lib/db/schema";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const [result] = await db
    .select()
    .from(variety)
    .where(eq(variety.id, parseInt(id)));

  if (!result) {
    return NextResponse.json({ error: "品种不存在" }, { status: 404 });
  }
  return NextResponse.json(result);
}

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await request.json();

  await db
    .update(variety)
    .set({
      name: body.name,
      appearance: body.appearance,
      difficulty: body.difficulty,
      growthHabit: body.growthHabit,
      suitableScene: body.suitableScene,
      marketPrice: body.marketPrice,
      popularityRating: body.popularityRating,
      seasonalIndex: body.seasonalIndex
        ? JSON.stringify(body.seasonalIndex)
        : null,
      customerFeedback: body.customerFeedback,
      showInFrontend: body.showInFrontend ? 1 : 0,
      frontendDescription: body.frontendDescription,
      coverImage: body.coverImage,
    })
    .where(eq(variety.id, parseInt(id)));

  return NextResponse.json({ success: true });
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  await db.delete(variety).where(eq(variety.id, parseInt(id)));
  return NextResponse.json({ success: true });
}
