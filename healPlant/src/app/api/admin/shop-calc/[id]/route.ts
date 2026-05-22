import { db } from "@/lib/db";
import { shopCost } from "@/lib/db/schema";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  await db.delete(shopCost).where(eq(shopCost.id, parseInt(id)));
  return NextResponse.json({ success: true });
}
