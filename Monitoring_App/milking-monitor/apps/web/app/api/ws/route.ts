import { subscribe, unsubscribe } from "../../../lib/realtime/broadcast";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const sessionId = url.searchParams.get("session_id");

  if (!sessionId) {
    return Response.json({ ok: false, error: "session_id is required" }, { status: 400 });
  }

  let subscriberController: ReadableStreamDefaultController<string> | null = null;

  const stream = new ReadableStream<string>({
    start(controller) {
      subscriberController = controller;
      subscribe(sessionId, controller);
      controller.enqueue(`data: ${JSON.stringify({ session_id: sessionId, type: "connected", payload: {} })}\n\n`);
    },
    cancel() {
      if (subscriberController) {
        unsubscribe(sessionId, subscriberController);
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
