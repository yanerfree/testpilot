import { db } from "@/lib/db";
import { sale, purchase, wastage } from "@/lib/db/schema";
import { sql, gte, lte, and } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const dateFrom = searchParams.get("dateFrom") || "2000-01-01";
  const dateTo = searchParams.get("dateTo") || "2099-12-31";

  const purchaseConditions = and(
    gte(purchase.purchaseDate, dateFrom),
    lte(purchase.purchaseDate, dateTo)
  );
  const saleConditions = and(
    gte(sale.saleDate, dateFrom),
    lte(sale.saleDate, dateTo)
  );
  const wastageConditions = and(
    gte(wastage.wastageDate, dateFrom),
    lte(wastage.wastageDate, dateTo)
  );

  const [purchaseSummary] = await db
    .select({ total: sql<number>`coalesce(sum(${purchase.totalCost}), 0)` })
    .from(purchase)
    .where(purchaseConditions);

  const [saleSummary] = await db
    .select({
      totalRevenue: sql<number>`coalesce(sum(${sale.totalRevenue}), 0)`,
      totalProfit: sql<number>`coalesce(sum(${sale.profit}), 0)`,
      totalSold: sql<number>`coalesce(sum(${sale.quantity}), 0)`,
    })
    .from(sale)
    .where(saleConditions);

  const [wastageSummary] = await db
    .select({
      totalLoss: sql<number>`coalesce(sum(${wastage.totalLoss}), 0)`,
      totalWasted: sql<number>`coalesce(sum(${wastage.quantity}), 0)`,
    })
    .from(wastage)
    .where(wastageConditions);

  const totalPurchase = purchaseSummary.total;
  const totalRevenue = saleSummary.totalRevenue;
  const totalProfit = saleSummary.totalProfit;
  const totalSold = saleSummary.totalSold;
  const totalWasted = wastageSummary.totalWasted;
  const totalLoss = wastageSummary.totalLoss;

  const grossMargin =
    totalRevenue > 0
      ? ((totalRevenue - totalPurchase) / totalRevenue) * 100
      : 0;

  const wastageRate =
    totalSold + totalWasted > 0
      ? (totalWasted / (totalSold + totalWasted)) * 100
      : 0;

  return NextResponse.json({
    totalPurchase,
    totalRevenue,
    totalProfit,
    grossMargin: Math.round(grossMargin * 10) / 10,
    totalWasted,
    totalLoss,
    wastageRate: Math.round(wastageRate * 10) / 10,
    balance: totalRevenue - totalPurchase - totalLoss,
  });
}
