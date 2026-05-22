import { db } from "@/lib/db";
import { aboutPage } from "@/lib/db/schema";
import { eq } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET() {
  const [result] = await db.select().from(aboutPage).limit(1);

  if (!result) {
    return NextResponse.json({ content: "" });
  }
  return NextResponse.json(result);
}

export async function PUT(request: Request) {
  const body = await request.json();

  const [existing] = await db.select().from(aboutPage).limit(1);

  if (existing) {
    await db
      .update(aboutPage)
      .set({ content: body.content })
      .where(eq(aboutPage.id, existing.id));
  } else {
    await db.insert(aboutPage).values({ content: body.content });
  }

  return NextResponse.json({ success: true });
}
