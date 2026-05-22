import { db } from "@/lib/db";
import { shopCost } from "@/lib/db/schema";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET() {
  const costs = await db.select().from(shopCost);
  return NextResponse.json(costs);
}

export async function POST(request: Request) {
  const body = await request.json();
  if (!body.name || !body.amount || !body.frequency) {
    return NextResponse.json({ error: "缺少必填字段" }, { status: 400 });
  }

  const freqMap: Record<string, number> = {
    monthly: 1,
    quarterly: 3,
    yearly: 12,
  };
  const monthlyAmount = body.amount / (freqMap[body.frequency] || 1);

  const [result] = await db
    .insert(shopCost)
    .values({
      name: body.name,
      amount: body.amount,
      frequency: body.frequency,
      category: body.category || null,
      monthlyAmount: Math.round(monthlyAmount * 100) / 100,
    })
    .returning();

  return NextResponse.json(result);
}
