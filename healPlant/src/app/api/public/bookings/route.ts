import { db } from "@/lib/db";
import { booking } from "@/lib/db/schema";
import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const body = await request.json();
  const { customerName, phone, address, requirement } = body;

  if (!customerName || !phone) {
    return NextResponse.json(
      { error: "姓名和电话必填" },
      { status: 400 }
    );
  }

  const phoneRegex = /^1[3-9]\d{9}$/;
  if (!phoneRegex.test(phone)) {
    return NextResponse.json(
      { error: "请输入正确的手机号" },
      { status: 400 }
    );
  }

  await db.insert(booking).values({
    customerName: customerName.trim(),
    phone: phone.trim(),
    address: address?.trim() || null,
    requirement: requirement?.trim() || null,
  });

  return NextResponse.json({ success: true });
}
