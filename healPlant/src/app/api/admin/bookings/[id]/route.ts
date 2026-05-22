import { db } from "@/lib/db";
import { booking } from "@/lib/db/schema";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await request.json();

  await db
    .update(booking)
    .set({
      status: body.status,
    })
    .where(eq(booking.id, parseInt(id)));

  return NextResponse.json({ success: true });
}
