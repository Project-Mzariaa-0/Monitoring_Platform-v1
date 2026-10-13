import { updateSessionEmployee } from "../../../../../lib/data/store";
import { updateSessionEmployeeSchema } from "../../../../../lib/validation/session";
import { getApiSession, requireApiSession } from "../../../../../lib/auth/api";
import { rateLimit } from "../../../../../lib/security/rate-limit";

export async function PATCH(request: Request, { params }: { params: Promise<{ sessionId: string }> }) {
  const unauthorized = await requireApiSession();
  if (unauthorized) return unauthorized;

  const { sessionId } = await params;
  const body = await request.json().catch(() => null);

  if (!body) {
    return Response.json({ ok: false, error: "Invalid JSON body" }, { status: 400 });
  }

  const parsed = updateSessionEmployeeSchema.safeParse(body);
  if (!parsed.success) {
    return Response.json(
      { ok: false, error: "Validation failed", details: parsed.error.flatten().fieldErrors },
      { status: 422 },
    );
  }

  const session = await getApiSession();
  const actorId = (session?.user as { id?: string } | undefined)?.id;
  if (!actorId) {
    return Response.json({ ok: false, error: "Unauthorized" }, { status: 401 });
  }

  const limit = rateLimit(`sessions:employee:${actorId}`, 30, 60_000);
  if (!limit.allowed) {
    return Response.json({ ok: false, error: "Rate limit exceeded" }, { status: 429 });
  }

  const updated = await updateSessionEmployee(
    sessionId,
    parsed.data.employee_id,
    parsed.data.employee_name,
    actorId,
  );

  if (!updated) {
    return Response.json({ ok: false, error: "Session not found" }, { status: 404 });
  }

  return Response.json({ ok: true, route: "sessions:employee:update", data: updated });
}
