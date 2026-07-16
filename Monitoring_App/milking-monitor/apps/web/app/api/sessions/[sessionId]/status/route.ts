import { rateLimit } from "../../../../../lib/security/rate-limit";
import { updateSessionStatus } from "../../../../../lib/data/store";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ sessionId: string }> },
) {
  const clientId = request.headers.get("x-forwarded-for") ?? "anonymous";
  const limit = rateLimit(`sessions:status:${clientId}`, 60, 60_000);

  if (!limit.allowed) {
    return Response.json({ ok: false, error: "Rate limit exceeded" }, { status: 429 });
  }

  const { sessionId } = await params;
  const body = await request.json().catch(() => null);
  if (!body || !body.status) {
    return Response.json({ ok: false, error: "status field is required" }, { status: 400 });
  }

  const validStatuses = ["scheduled", "active", "completed", "ended_early"];
  if (!validStatuses.includes(body.status)) {
    return Response.json({ ok: false, error: `Invalid status. Must be one of: ${validStatuses.join(", ")}` }, { status: 400 });
  }

  try {
    const updated = await updateSessionStatus(sessionId, body.status);
    if (!updated) {
      return Response.json({ ok: false, error: "Session not found" }, { status: 404 });
    }
    return Response.json({ ok: true, data: updated });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return Response.json({ ok: false, error: message }, { status: 500 });
  }
}
