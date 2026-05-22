import { db } from "@/lib/db";
import { purchase } from "@/lib/db/schema";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  await db.delete(purchase).where(eq(purchase.id, parseInt(id)));
  return NextResponse.json({ success: true });
}
