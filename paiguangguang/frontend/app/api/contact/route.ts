import { NextResponse } from "next/server";

import { createContactTransporter, getContactRecipient, getMailFrom } from "@/lib/mail";

export const runtime = "nodejs";

type ContactPayload = {
  name?: unknown;
  email?: unknown;
  message?: unknown;
  website?: unknown;
};

function asTrimmedString(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function isValidEmail(email: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export async function POST(request: Request) {
  let body: ContactPayload;

  try {
    body = (await request.json()) as ContactPayload;
  } catch {
    return NextResponse.json({ ok: false, error: "Invalid JSON body" }, { status: 400 });
  }

  if (asTrimmedString(body.website)) {
    return NextResponse.json({ ok: true });
  }

  const name = asTrimmedString(body.name);
  const email = asTrimmedString(body.email);
  const message = asTrimmedString(body.message);

  if (!name || !email || !message) {
    return NextResponse.json({ ok: false, error: "Please complete all fields" }, { status: 400 });
  }

  if (!isValidEmail(email)) {
    return NextResponse.json({ ok: false, error: "Please enter a valid email address" }, { status: 400 });
  }

  try {
    const transporter = createContactTransporter();
    const from = getMailFrom();

    if (!from) {
      return NextResponse.json({ ok: false, error: "Missing MAIL_FROM configuration" }, { status: 500 });
    }

    await transporter.sendMail({
      from,
      to: getContactRecipient(),
      replyTo: email,
      subject: `Portfolio contact from ${name}`,
      text: `${message}\n\nFrom: ${name} <${email}>`
    });

    return NextResponse.json({ ok: true });
  } catch (error) {
    const messageText = error instanceof Error ? error.message : "Failed to send email";
    return NextResponse.json({ ok: false, error: messageText }, { status: 500 });
  }
}
