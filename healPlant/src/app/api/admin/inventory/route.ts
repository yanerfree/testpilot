import { db } from "@/lib/db";
import { inventory, variety } from "@/lib/db/schema";
import { desc, eq } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const status = searchParams.get("condition");
  const category = searchParams.get("category");

  let query = db
    .select({
      id: inventory.id,
      varietyId: inventory.varietyId,
      varietyName: variety.name,
      quantity: inventory.quantity,
      location: inventory.location,
      condition: inventory.condition,
      category: inventory.category,
      updatedAt: inventory.updatedAt,
    })
    .from(inventory)
    .leftJoin(variety, eq(inventory.varietyId, variety.id))
    .orderBy(desc(inventory.updatedAt))
    .$dynamic();

  if (status) query = query.where(eq(inventory.condition, status as "good" | "needs-care" | "pending"));
  if (category) query = query.where(eq(inventory.category, category as "for-sale" | "for-care"));

  const results = await query.limit(200);
  return NextResponse.json(results);
}

export async function POST(request: Request) {
  const body = await request.json();
  if (!body.varietyId || !body.quantity || !body.condition || !body.category) {
    return NextResponse.json({ error: "缺少必填字段" }, { status: 400 });
  }

  const [result] = await db
    .insert(inventory)
    .values({
      varietyId: body.varietyId,
      quantity: body.quantity,
      location: body.location || null,
      condition: body.condition,
      category: body.category,
    })
    .returning();

  return NextResponse.json(result);
}
