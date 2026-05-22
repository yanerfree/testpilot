import { db } from "@/lib/db";
import { guestbook } from "@/lib/db/schema";
import { desc, eq } from "drizzle-orm";
import { NextResponse } from "next/server";

export async function GET() {
  const entries = await db
    .select({
      id: guestbook.id,
      nickname: guestbook.nickname,
      message: guestbook.message,
      adminReply: guestbook.adminReply,
      createdAt: guestbook.createdAt,
    })
    .from(guestbook)
    .where(eq(guestbook.isVisible, 1))
    .orderBy(desc(guestbook.createdAt))
    .limit(50);

  return NextResponse.json(entries);
}

export async function POST(request: Request) {
  const body = await request.json();
  const { nickname, message } = body;

  if (
    !nickname ||
    !message ||
    typeof nickname !== "string" ||
    typeof message !== "string"
  ) {
    return NextResponse.json({ error: "昵称和留言内容必填" }, { status: 400 });
  }

  if (nickname.length > 50 || message.length > 500) {
    return NextResponse.json({ error: "内容过长" }, { status: 400 });
  }

  await db.insert(guestbook).values({
    nickname: nickname.trim(),
    message: message.trim(),
  });

  return NextResponse.json({ success: true });
}
