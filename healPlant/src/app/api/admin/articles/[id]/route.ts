import { db } from "@/lib/db";
import { article } from "@/lib/db/schema";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await request.json();

  await db
    .update(article)
    .set({
      title: body.title,
      body: body.body,
      category: body.category,
      coverImage: body.coverImage,
      videoId: body.videoId,
      isPublished: body.isPublished ? 1 : 0,
    })
    .where(eq(article.id, parseInt(id)));

  return NextResponse.json({ success: true });
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  await db.delete(article).where(eq(article.id, parseInt(id)));
  return NextResponse.json({ success: true });
}
