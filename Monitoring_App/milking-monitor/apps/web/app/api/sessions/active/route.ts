import { rateLimit } from "../../../../lib/security/rate-limit";
import { listActiveSessions } from "../../../../lib/data/store";

export async function GET(request: Request) {
  const clientId = request.headers.get("x-forwarded-for") ?? "anonymous";
  const limit = rateLimit(`sessions:active:${clientId}`, 60, 60_000);

  if (!limit.allowed) {
    return Response.json({ ok: false, error: "Rate limit exceeded" }, { status: 429 });
  }

  try {
    const sessions = await listActiveSessions();
    return Response.json({ ok: true, data: sessions });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return Response.json({ ok: false, error: message }, { status: 500 });
  }
}
