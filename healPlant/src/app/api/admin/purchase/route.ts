import { db } from "@/lib/db";
import { purchase, variety } from "@/lib/db/schema";
import { desc, gte, lte, and, eq } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const dateFrom = searchParams.get("dateFrom");
  const dateTo = searchParams.get("dateTo");

  const conditions = [];
  if (dateFrom) conditions.push(gte(purchase.purchaseDate, dateFrom));
  if (dateTo) conditions.push(lte(purchase.purchaseDate, dateTo));

  const results = await db
    .select({
      id: purchase.id,
      varietyId: purchase.varietyId,
      varietyName: variety.name,
      quantity: purchase.quantity,
      unitPrice: purchase.unitPrice,
      totalCost: purchase.totalCost,
      purchaseDate: purchase.purchaseDate,
      note: purchase.note,
      createdAt: purchase.createdAt,
    })
    .from(purchase)
    .leftJoin(variety, eq(purchase.varietyId, variety.id))
    .orderBy(desc(purchase.purchaseDate))
    .where(conditions.length > 0 ? and(...conditions) : undefined)
    .limit(200);

  return NextResponse.json(results);
}

export async function POST(request: Request) {
  const body = await request.json();

  if (!body.varietyId || !body.quantity || !body.unitPrice || !body.purchaseDate) {
    return NextResponse.json({ error: "缺少必填字段" }, { status: 400 });
  }

  const totalCost = body.quantity * body.unitPrice;

  const [result] = await db
    .insert(purchase)
    .values({
      varietyId: body.varietyId,
      quantity: body.quantity,
      unitPrice: body.unitPrice,
      totalCost,
      purchaseDate: body.purchaseDate,
      note: body.note || null,
    })
    .returning();

  return NextResponse.json(result);
}
