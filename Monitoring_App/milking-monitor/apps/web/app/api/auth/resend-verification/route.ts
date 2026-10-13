import { eq } from "drizzle-orm";
import { z } from "zod";
import { db } from "../../../../lib/db/client";
import { users } from "../../../../lib/db/schema";
import { createEmailVerificationToken } from "../../../../lib/auth/verification";
import { buildVerificationUrl, sendVerificationEmail } from "../../../../lib/email/mailer";
import { rateLimit } from "../../../../lib/security/rate-limit";

const resendSchema = z.object({
  email: z.string().trim().toLowerCase().email().max(320),
}).strict();

export async function POST(request: Request) {
  const clientId = request.headers.get("x-forwarded-for") ?? "anonymous";
  const limit = rateLimit(`auth:resend:${clientId}`, 3, 15 * 60_000);

  if (!limit.allowed) {
    return Response.json({ ok: false, error: "Too many resend attempts. Try again later." }, { status: 429 });
  }

  const body = await request.json().catch(() => null);
  const parsed = resendSchema.safeParse(body);
  if (!parsed.success) {
    return Response.json(
      { ok: false, error: "Invalid email", details: parsed.error.flatten().fieldErrors },
      { status: 422 },
    );
  }

  try {
    const [user] = await db
      .select({ id: users.id, email: users.email, name: users.name, emailVerified: users.emailVerified })
      .from(users)
      .where(eq(users.email, parsed.data.email))
      .limit(1);

    // Same response whether or not the account exists (no enumeration).
    if (!user || user.emailVerified) {
      return Response.json({ ok: true, data: { resent: true } });
    }

    const token = await createEmailVerificationToken(user.email);
    const origin = process.env.NEXTAUTH_URL ?? new URL(request.url).origin;
    const result = await sendVerificationEmail({
      to: user.email,
      name: user.name ?? "there",
      verifyUrl: buildVerificationUrl(origin, user.email, token),
    });

    if (!result.sent) {
      return Response.json({ ok: false, error: result.error ?? "Could not send verification email" }, { status: 502 });
    }
    return Response.json({ ok: true, data: { resent: true } });
  } catch (error) {
    console.error("[auth] resend verification failed", error);
    return Response.json({ ok: false, error: "Service temporarily unavailable" }, { status: 503 });
  }
}
