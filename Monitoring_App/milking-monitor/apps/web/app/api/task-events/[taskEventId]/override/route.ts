import { overrideTaskEvent } from "../../../../../lib/data/store";
import { overrideTaskEventSchema } from "../../../../../lib/validation/task-event";
import { getApiSession, requireApiSession } from "../../../../../lib/auth/api";
import { rateLimit } from "../../../../../lib/security/rate-limit";

export async function PATCH(request: Request, { params }: { params: Promise<{ taskEventId: string }> }) {
  const unauthorized = await requireApiSession();
  if (unauthorized) return unauthorized;

  const { taskEventId } = await params;
  const body = await request.json().catch(() => null);

  if (!body) {
    return Response.json({ ok: false, error: "Invalid JSON body" }, { status: 400 });
  }

  const parsed = overrideTaskEventSchema.safeParse(body);
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

  const limit = rateLimit(`task-events:override:${actorId}`, 30, 60_000);
  if (!limit.allowed) {
    return Response.json({ ok: false, error: "Rate limit exceeded" }, { status: 429 });
  }

  const updated = await overrideTaskEvent(
    taskEventId,
    parsed.data.override_status,
    parsed.data.reason,
    actorId,
  );

  if (!updated) {
    return Response.json({ ok: false, error: "Task event not found" }, { status: 404 });
  }

  return Response.json({ ok: true, route: "task-events:override", data: updated });
}
