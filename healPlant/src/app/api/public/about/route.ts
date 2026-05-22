import { db } from "@/lib/db";
import { aboutPage } from "@/lib/db/schema";
import { NextResponse } from "next/server";

export async function GET() {
  const [result] = await db.select().from(aboutPage).limit(1);

  if (!result) {
    return NextResponse.json({ content: "" });
  }
  return NextResponse.json(result);
}
