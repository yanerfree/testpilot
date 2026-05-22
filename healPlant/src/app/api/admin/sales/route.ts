import { db } from "@/lib/db";
import { sale, purchase } from "@/lib/db/schema";
import { desc, eq, gte, lte, and } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const dateFrom = searchParams.get("dateFrom");
  const dateTo = searchParams.get("dateTo");

  const conditions = [];
  if (dateFrom) conditions.push(gte(sale.saleDate, dateFrom));
  if (dateTo) conditions.push(lte(sale.saleDate, dateTo));

  const results = await db
    .select()
    .from(sale)
    .orderBy(desc(sale.saleDate))
    .where(conditions.length > 0 ? and(...conditions) : undefined)
    .limit(200);

  return NextResponse.json(results);
}

export async function POST(request: Request) {
  const body = await request.json();

  if (
    !body.varietyId ||
    !body.quantity ||
    !body.unitSalePrice ||
    !body.saleDate
  ) {
    return NextResponse.json({ error: "缺少必填字段" }, { status: 400 });
  }

  const [latestPurchase] = await db
    .select({ unitPrice: purchase.unitPrice })
    .from(purchase)
    .where(eq(purchase.varietyId, body.varietyId))
    .orderBy(desc(purchase.createdAt))
    .limit(1);

  const costBasis = latestPurchase?.unitPrice || 0;
  const totalRevenue = body.quantity * body.unitSalePrice;
  const profit = totalRevenue - costBasis * body.quantity;

  const [result] = await db
    .insert(sale)
    .values({
      varietyId: body.varietyId,
      quantity: body.quantity,
      unitSalePrice: body.unitSalePrice,
      totalRevenue,
      costBasis,
      profit,
      saleDate: body.saleDate,
      note: body.note || null,
    })
    .returning();

  return NextResponse.json(result);
}
