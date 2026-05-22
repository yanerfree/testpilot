import { db } from "@/lib/db";
import { inventory } from "@/lib/db/schema";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await request.json();
  await db
    .update(inventory)
    .set({
      quantity: body.quantity,
      location: body.location,
      condition: body.condition,
      category: body.category,
    })
    .where(eq(inventory.id, parseInt(id)));

  return NextResponse.json({ success: true });
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  await db.delete(inventory).where(eq(inventory.id, parseInt(id)));
  return NextResponse.json({ success: true });
}
