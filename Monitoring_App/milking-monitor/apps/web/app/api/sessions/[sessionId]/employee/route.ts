import { updateSessionEmployee } from "../../../../../lib/data/store";
import { updateSessionEmployeeSchema } from "../../../../../lib/validation/session";

export async function PATCH(request: Request, { params }: { params: Promise<{ sessionId: string }> }) {
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

  const updated = await updateSessionEmployee(
    sessionId,
    parsed.data.employee_id,
    parsed.data.employee_name,
    parsed.data.actor_id,
  );

  if (!updated) {
    return Response.json({ ok: false, error: "Session not found" }, { status: 404 });
  }

  return Response.json({ ok: true, route: "sessions:employee:update", data: updated });
}
