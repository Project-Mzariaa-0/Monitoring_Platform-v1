import { overrideTaskEvent } from "../../../../../lib/data/store";
import { overrideTaskEventSchema } from "../../../../../lib/validation/task-event";

export async function PATCH(request: Request, { params }: { params: Promise<{ taskEventId: string }> }) {
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

  const updated = await overrideTaskEvent(
    taskEventId,
    parsed.data.override_status,
    parsed.data.reason,
    parsed.data.actor_id,
  );

  if (!updated) {
    return Response.json({ ok: false, error: "Task event not found" }, { status: 404 });
  }

  return Response.json({ ok: true, route: "task-events:override", data: updated });
}
