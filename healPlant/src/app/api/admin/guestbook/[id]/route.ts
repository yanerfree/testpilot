import { db } from "@/lib/db";
import { guestbook } from "@/lib/db/schema";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await request.json();

  await db
    .update(guestbook)
    .set({
      adminReply: body.adminReply,
      isVisible: body.isVisible ? 1 : 0,
      repliedAt: body.adminReply ? new Date().toISOString() : undefined,
    })
    .where(eq(guestbook.id, parseInt(id)));

  return NextResponse.json({ success: true });
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  await db.delete(guestbook).where(eq(guestbook.id, parseInt(id)));
  return NextResponse.json({ success: true });
}
