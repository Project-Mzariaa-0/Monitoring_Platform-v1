import { rateLimit } from "../../../lib/security/rate-limit";
import { createSession, listSessions } from "../../../lib/data/store";
import { notifySessionWindow } from "../../../lib/inference-client/notify-session-window";
import { createSessionSchema } from "../../../lib/validation/session";

export async function GET(request: Request) {
  const clientId = request.headers.get("x-forwarded-for") ?? "anonymous";
  const limit = rateLimit(`sessions:get:${clientId}`, 120, 60_000);

  if (!limit.allowed) {
    return Response.json({ ok: false, error: "Rate limit exceeded" }, { status: 429 });
  }

  const sessions = await listSessions();
  return Response.json({ ok: true, route: "sessions:list", data: sessions });
}

export async function POST(request: Request) {
  const clientId = request.headers.get("x-forwarded-for") ?? "anonymous";
  const limit = rateLimit(`sessions:post:${clientId}`, 20, 60_000);

  if (!limit.allowed) {
    return Response.json({ ok: false, error: "Rate limit exceeded" }, { status: 429 });
  }

  const body = await request.json().catch(() => null);
  if (!body) {
    return Response.json({ ok: false, error: "Invalid JSON body" }, { status: 400 });
  }

  const parsed = createSessionSchema.safeParse(body);
  if (!parsed.success) {
    return Response.json(
      { ok: false, error: "Validation failed", details: parsed.error.flatten().fieldErrors },
      { status: 422 },
    );
  }

  try {
    const session = await createSession(parsed.data);

    let inferenceWarning: string | null = null;
    try {
      await notifySessionWindow(
        session.id,
        parsed.data.scheduled_start_time,
        parsed.data.estimated_end_time,
      );
    } catch (inferenceError) {
      inferenceWarning = inferenceError instanceof Error ? inferenceError.message : "Inference service unavailable";
    }

    const response: Record<string, unknown> = { ok: true, route: "sessions:create", data: session };
    if (inferenceWarning) {
      response.warning = inferenceWarning;
    }

    return Response.json(response, { status: 201 });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    const status = message.includes("not found") ? 404 : 500;
    return Response.json({ ok: false, error: message }, { status });
  }
}
