import { db } from "@/lib/db";
import { wastage, purchase } from "@/lib/db/schema";
import { desc, eq, gte, lte, and } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const dateFrom = searchParams.get("dateFrom");
  const dateTo = searchParams.get("dateTo");

  const conditions = [];
  if (dateFrom) conditions.push(gte(wastage.wastageDate, dateFrom));
  if (dateTo) conditions.push(lte(wastage.wastageDate, dateTo));

  const results = await db
    .select()
    .from(wastage)
    .orderBy(desc(wastage.wastageDate))
    .where(conditions.length > 0 ? and(...conditions) : undefined)
    .limit(200);

  return NextResponse.json(results);
}

export async function POST(request: Request) {
  const body = await request.json();

  if (!body.varietyId || !body.quantity || !body.reason || !body.wastageDate) {
    return NextResponse.json({ error: "缺少必填字段" }, { status: 400 });
  }

  const [latestPurchase] = await db
    .select({ unitPrice: purchase.unitPrice })
    .from(purchase)
    .where(eq(purchase.varietyId, body.varietyId))
    .orderBy(desc(purchase.createdAt))
    .limit(1);

  const costBasis = latestPurchase?.unitPrice || 0;
  const totalLoss = body.quantity * costBasis;

  const [result] = await db
    .insert(wastage)
    .values({
      varietyId: body.varietyId,
      quantity: body.quantity,
      reason: body.reason,
      costBasis,
      totalLoss,
      wastageDate: body.wastageDate,
      note: body.note || null,
    })
    .returning();

  return NextResponse.json(result);
}
