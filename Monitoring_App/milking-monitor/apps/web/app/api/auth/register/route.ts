import { eq } from "drizzle-orm";
import { z } from "zod";
import { db } from "../../../../lib/db/client";
import { users } from "../../../../lib/db/schema";
import { hashPassword } from "../../../../lib/auth/password";
import { createEmailVerificationToken } from "../../../../lib/auth/verification";
import { buildVerificationUrl, sendVerificationEmail } from "../../../../lib/email/mailer";
import { rateLimit } from "../../../../lib/security/rate-limit";

const registerSchema = z.object({
  email: z.string().trim().toLowerCase().email().max(320),
  password: z.string().min(12).max(128),
  name: z.string().trim().min(2).max(120),
}).strict();

export async function POST(request: Request) {
  const clientId = request.headers.get("x-forwarded-for") ?? "anonymous";
  const limit = rateLimit(`auth:register:${clientId}`, 5, 15 * 60_000);

  if (!limit.allowed) {
    return Response.json({ ok: false, error: "Too many registration attempts" }, { status: 429 });
  }

  const body = await request.json().catch(() => null);
  const parsed = registerSchema.safeParse(body);
  if (!parsed.success) {
    return Response.json(
      { ok: false, error: "Invalid registration details", details: parsed.error.flatten().fieldErrors },
      { status: 422 },
    );
  }

  try {
    const [existingUser] = await db
      .select({ id: users.id })
      .from(users)
      .where(eq(users.email, parsed.data.email))
      .limit(1);

    if (existingUser) {
      return Response.json({ ok: false, error: "An account with this email already exists" }, { status: 409 });
    }
  } catch (error) {
    console.error("[auth] registration lookup failed", error);
    return Response.json({ ok: false, error: "Registration service temporarily unavailable" }, { status: 503 });
  }

  try {
    const [createdUser] = await db
      .insert(users)
      .values({
        id: crypto.randomUUID(),
        email: parsed.data.email,
        name: parsed.data.name,
        emailVerified: null,
        password_hash: hashPassword(parsed.data.password),
        registration_completed_at: null,
      })
      .returning({ id: users.id, email: users.email, name: users.name });

    if (!createdUser) {
      return Response.json({ ok: false, error: "Account could not be created" }, { status: 500 });
    }

    let verificationEmailSent = false;
    let verificationError: string | undefined;
    try {
      const token = await createEmailVerificationToken(createdUser.email);
      const origin = process.env.NEXTAUTH_URL ?? new URL(request.url).origin;
      const verifyUrl = buildVerificationUrl(origin, createdUser.email, token);
      const result = await sendVerificationEmail({
        to: createdUser.email,
        name: createdUser.name ?? "there",
        verifyUrl,
      });
      verificationEmailSent = result.sent;
      verificationError = result.error;
    } catch (error) {
      console.error("[auth] verification email failed", error);
      verificationError = error instanceof Error ? error.message : "Unknown email error";
    }

    return Response.json(
      { ok: true, data: createdUser, verificationEmailSent, ...(verificationError ? { verificationError } : {}) },
      { status: 201 },
    );
  } catch (error) {
    console.error("[auth] registration failed", error);
    return Response.json({ ok: false, error: "Account could not be created" }, { status: 500 });
  }
}