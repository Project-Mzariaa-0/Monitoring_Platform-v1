import { publish } from "../../../../lib/realtime/broadcast";
import { ingestTaskEvent, updateCowProcess } from "../../../../lib/data/store";
import { buildTaskEventFingerprint } from "../../../../lib/data/event-dedupe";
import { ingestEventContractSchema } from "../../../../lib/validation/event-contract";
import { rateLimit } from "../../../../lib/security/rate-limit";

export async function POST(request: Request) {
  const requestId = request.headers.get("x-request-id") || crypto.randomUUID();
  const jsonResponse = (body: unknown, init?: ResponseInit) => {
    const headers = new Headers(init?.headers);
    headers.set("x-request-id", requestId);
    return Response.json(body, { ...init, headers });
  };
  const log = (message: string, fields: Record<string, unknown> = {}) => {
    console.info(JSON.stringify({ timestamp: new Date().toISOString(), request_id: requestId, message, ...fields }));
  };
  const expectedToken = process.env.INFERENCE_SERVICE_TOKEN;
  const authorization = request.headers.get("authorization");
  const clientId = authorization ?? request.headers.get("x-forwarded-for") ?? "anonymous";
  const limit = rateLimit(`ingest:${clientId}`, 120, 60_000);

  if (!limit.allowed) {
    return jsonResponse({ ok: false, error: "Rate limit exceeded" }, { status: 429, headers: { "Retry-After": String(Math.ceil((limit.resetAt - Date.now()) / 1000)) } });
  }

  if (!expectedToken) {
    return jsonResponse({ ok: false, error: "Server misconfiguration: INFERENCE_SERVICE_TOKEN not set" }, { status: 500 });
  }

  if (authorization !== `Bearer ${expectedToken}`) {
    return jsonResponse({ ok: false, error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json().catch(() => null);
  if (!body) {
    return jsonResponse({ ok: false, error: "Invalid JSON body" }, { status: 400 });
  }

  const parsed = ingestEventContractSchema.safeParse(body);
  if (!parsed.success) {
    return jsonResponse(
      { ok: false, error: "Validation failed", details: parsed.error.flatten().fieldErrors },
      { status: 422 },
    );
  }

  const { session_id: sessionId } = parsed.data;

  const taskFingerprint = parsed.data.event_type === "task_event"
    ? buildTaskEventFingerprint({
        session_id: sessionId,
        cow_position: parsed.data.cow_position,
        task_id: parsed.data.task_id,
        status: parsed.data.status,
        detected_start_time: parsed.data.detected_start_time,
        detected_end_time: parsed.data.detected_end_time,
        duration_seconds: parsed.data.duration_seconds,
      })
    : null;

  if (parsed.data.event_type === "task_event") {
    try {
      const persisted = await ingestTaskEvent({
        session_id: sessionId,
        cow_position: parsed.data.cow_position,
        task_id: parsed.data.task_id,
        status: parsed.data.status,
        confidence_score: parsed.data.confidence_score,
        completion_percentage: parsed.data.completion_percentage,
        detected_start_time: parsed.data.detected_start_time,
        detected_end_time: parsed.data.detected_end_time,
        duration_seconds: parsed.data.duration_seconds,
      });
      if (!persisted) {
        console.warn(
          `[ingest] Task event dropped (no matching cow process): session=${sessionId} position=${parsed.data.cow_position} task=${parsed.data.task_id}`,
        );
        return jsonResponse({ ok: false, error: "No matching cow process for session" }, { status: 404 });
      }

      if (taskFingerprint && persisted) {
        log("Task event accepted", { event_type: "task_event", session_id: sessionId, fingerprint: taskFingerprint });
      }
    } catch (error) {
      console.error("Failed to persist task event", error);
      return jsonResponse({ ok: false, error: "Failed to persist task event" }, { status: 500 });
    }
  }

  if (parsed.data.event_type === "cow_process") {
    try {
      await updateCowProcess(sessionId, parsed.data.cow_position, parsed.data.process_status, parsed.data.detected_time);
    } catch (error) {
      console.error("Failed to update cow process", error);
    }
  }

  publish(sessionId, {
    session_id: sessionId,
    type: parsed.data.event_type === "task_event" ? parsed.data.task_id : parsed.data.event_type,
    payload: parsed.data,
  });

  log("Event ingested", { event_type: parsed.data.event_type, session_id: sessionId });
  return jsonResponse({ ok: true, route: "events:ingest" });
}
