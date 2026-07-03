import { publish } from "../../../../lib/realtime/broadcast";
import { ingestTaskEvent } from "../../../../lib/data/store";
import { rateLimit } from "../../../../lib/security/rate-limit";
import { z } from "zod";

const ingestEventSchema = z.object({
  session_id: z.string().uuid(),
  task_id: z.string().optional(),
  event_type: z.string().optional(),
  cow_position: z.number().int().min(1).max(2).optional(),
  status: z.enum(["completed", "missed", "anomaly_flagged", "unverifiable"]).optional(),
  confidence_score: z.number().min(0).max(1).optional(),
  detected_start_time: z.string().nullable().optional(),
  detected_end_time: z.string().nullable().optional(),
  duration_seconds: z.number().optional(),
}).passthrough();

export async function POST(request: Request) {
  const expectedToken = process.env.INFERENCE_SERVICE_TOKEN;
  const authorization = request.headers.get("authorization");
  const clientId = authorization ?? request.headers.get("x-forwarded-for") ?? "anonymous";
  const limit = rateLimit(`ingest:${clientId}`, 120, 60_000);

  if (!limit.allowed) {
    return Response.json({ ok: false, error: "Rate limit exceeded" }, { status: 429, headers: { "Retry-After": String(Math.ceil((limit.resetAt - Date.now()) / 1000)) } });
  }

  if (expectedToken && authorization !== `Bearer ${expectedToken}`) {
    return Response.json({ ok: false, error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json().catch(() => null);
  if (!body) {
    return Response.json({ ok: false, error: "Invalid JSON body" }, { status: 400 });
  }

  const parsed = ingestEventSchema.safeParse(body);
  if (!parsed.success) {
    return Response.json(
      { ok: false, error: "Validation failed", details: parsed.error.flatten().fieldErrors },
      { status: 422 },
    );
  }

  const { session_id: sessionId } = parsed.data;

  if (parsed.data.task_id && parsed.data.cow_position && parsed.data.status) {
    try {
      await ingestTaskEvent({
        session_id: sessionId,
        cow_position: parsed.data.cow_position as 1 | 2,
        task_id: parsed.data.task_id as "TASK-01" | "TASK-02" | "TASK-03" | "TASK-04" | "TASK-05" | "TASK-06",
        status: parsed.data.status,
        confidence_score: parsed.data.confidence_score,
        detected_start_time: (parsed.data as Record<string, unknown>).detected_start_time as string | null | undefined,
        detected_end_time: (parsed.data as Record<string, unknown>).detected_end_time as string | null | undefined,
        duration_seconds: (parsed.data as Record<string, unknown>).duration_seconds as number | undefined,
      });
    } catch {
      // DB write failed — events still broadcast via SSE
    }
  }

  publish(sessionId, {
    session_id: sessionId,
    type: parsed.data.event_type ?? parsed.data.task_id ?? "event",
    payload: parsed.data,
  });

  return Response.json({ ok: true, route: "events:ingest" });
}
