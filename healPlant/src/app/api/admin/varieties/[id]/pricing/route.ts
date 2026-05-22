import { db } from "@/lib/db";
import { pricingLog, purchase } from "@/lib/db/schema";
import { eq, desc } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const logs = await db
    .select()
    .from(pricingLog)
    .where(eq(pricingLog.varietyId, parseInt(id)))
    .orderBy(desc(pricingLog.createdAt))
    .limit(20);

  return NextResponse.json(logs);
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const varietyId = parseInt(id);
  const body = await request.json();

  let calculatedPrice: number;
  let baseCost: number | null = null;

  if (body.mode === "manual") {
    calculatedPrice = body.manualPrice;
  } else if (body.mode === "markup") {
    const [latestPurchase] = await db
      .select({ unitPrice: purchase.unitPrice })
      .from(purchase)
      .where(eq(purchase.varietyId, varietyId))
      .orderBy(desc(purchase.createdAt))
      .limit(1);

    if (!latestPurchase) {
      return NextResponse.json(
        { error: "该品种暂无进货记录，无法使用涨幅定价" },
        { status: 400 }
      );
    }

    baseCost = latestPurchase.unitPrice;
    calculatedPrice = baseCost * (1 + body.markupPercent / 100);
  } else {
    return NextResponse.json({ error: "无效的定价模式" }, { status: 400 });
  }

  const [result] = await db
    .insert(pricingLog)
    .values({
      varietyId,
      mode: body.mode,
      manualPrice: body.mode === "manual" ? body.manualPrice : null,
      markupPercent: body.mode === "markup" ? body.markupPercent : null,
      calculatedPrice,
      baseCost,
    })
    .returning();

  return NextResponse.json(result);
}
