import { db } from "@/lib/db";
import { content } from "@/lib/db/schema";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await request.json();

  await db
    .update(content)
    .set({
      type: body.type,
      title: body.title,
      body: body.body,
      images: body.images,
      videoId: body.videoId,
      isPublished: body.isPublished ? 1 : 0,
    })
    .where(eq(content.id, parseInt(id)));

  return NextResponse.json({ success: true });
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  await db.delete(content).where(eq(content.id, parseInt(id)));
  return NextResponse.json({ success: true });
}
