import { z } from "zod";
import { consumeEmailVerificationToken } from "../../../../lib/auth/verification";
import { rateLimit } from "../../../../lib/security/rate-limit";

const verifySchema = z.object({
  email: z.string().trim().toLowerCase().email().max(320),
  token: z.string().trim().min(16).max(256),
}).strict();

export async function POST(request: Request) {
  const clientId = request.headers.get("x-forwarded-for") ?? "anonymous";
  const limit = rateLimit(`auth:verify:${clientId}`, 10, 15 * 60_000);

  if (!limit.allowed) {
    return Response.json({ ok: false, error: "Too many verification attempts" }, { status: 429 });
  }

  const body = await request.json().catch(() => null);
  const parsed = verifySchema.safeParse(body);
  if (!parsed.success) {
    return Response.json(
      { ok: false, error: "Invalid verification details", details: parsed.error.flatten().fieldErrors },
      { status: 422 },
    );
  }

  try {
    const result = await consumeEmailVerificationToken(parsed.data.email, parsed.data.token);
    if (!result.ok) {
      return Response.json({ ok: false, error: result.error ?? "Verification failed" }, { status: 400 });
    }
    return Response.json({ ok: true, data: { email: parsed.data.email } });
  } catch (error) {
    console.error("[auth] verification failed", error);
    return Response.json({ ok: false, error: "Verification service temporarily unavailable" }, { status: 503 });
  }
}
