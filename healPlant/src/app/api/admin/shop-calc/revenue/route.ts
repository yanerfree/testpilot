import { db } from "@/lib/db";
import { shopRevenue } from "@/lib/db/schema";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET() {
  const [result] = await db.select().from(shopRevenue).limit(1);
  return NextResponse.json(result || null);
}

export async function PUT(request: Request) {
  const body = await request.json();
  const existing = await db.select().from(shopRevenue).limit(1);

  if (existing.length > 0) {
    await db
      .update(shopRevenue)
      .set({
        optimistic: body.optimistic,
        moderate: body.moderate,
        conservative: body.conservative,
        initialInvestment: body.initialInvestment || null,
      })
      .where(eq(shopRevenue.id, existing[0].id));
  } else {
    await db.insert(shopRevenue).values({
      optimistic: body.optimistic,
      moderate: body.moderate,
      conservative: body.conservative,
      initialInvestment: body.initialInvestment || null,
    });
  }

  return NextResponse.json({ success: true });
}
