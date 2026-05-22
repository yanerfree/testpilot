import { db } from "@/lib/db";
import { video } from "@/lib/db/schema";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await request.json();

  await db
    .update(video)
    .set({
      title: body.title,
      description: body.description,
      category: body.category,
      isPublic: body.isPublic ? 1 : 0,
    })
    .where(eq(video.id, parseInt(id)));

  return NextResponse.json({ success: true });
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  await db.delete(video).where(eq(video.id, parseInt(id)));
  return NextResponse.json({ success: true });
}
