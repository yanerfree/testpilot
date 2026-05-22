import { db } from "@/lib/db";
import { service } from "@/lib/db/schema";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await request.json();

  await db
    .update(service)
    .set({
      name: body.name,
      description: body.description,
      price: body.price,
      icon: body.icon,
      sortOrder: body.sortOrder,
    })
    .where(eq(service.id, parseInt(id)));

  return NextResponse.json({ success: true });
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  await db.delete(service).where(eq(service.id, parseInt(id)));
  return NextResponse.json({ success: true });
}
