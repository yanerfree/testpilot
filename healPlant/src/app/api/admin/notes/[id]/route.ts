import { db } from "@/lib/db";
import { note } from "@/lib/db/schema";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await request.json();

  await db
    .update(note)
    .set({
      title: body.title,
      body: body.body,
      tags: body.tags,
      noteDate: body.noteDate,
    })
    .where(eq(note.id, parseInt(id)));

  return NextResponse.json({ success: true });
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  await db.delete(note).where(eq(note.id, parseInt(id)));
  return NextResponse.json({ success: true });
}
