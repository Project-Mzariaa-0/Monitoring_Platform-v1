const INFERENCE_SERVICE_URL = process.env.INFERENCE_SERVICE_URL || "http://localhost:8001";
const INFERENCE_SERVICE_TOKEN = process.env.INFERENCE_SERVICE_TOKEN;

export async function notifySessionWindow(sessionId: string, startTime: string, endTime: string): Promise<void> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (INFERENCE_SERVICE_TOKEN) {
    headers["Authorization"] = `Bearer ${INFERENCE_SERVICE_TOKEN}`;
  }

  const response = await fetch(`${INFERENCE_SERVICE_URL}/session-window`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      session_id: sessionId,
      start_time: startTime,
      end_time: endTime,
      cow_positions: [1, 2],
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Failed to notify inference service: ${response.status} ${text}`);
  }
}

export async function stopSessionWindow(sessionId: string): Promise<void> {
  const headers: Record<string, string> = {};
  if (INFERENCE_SERVICE_TOKEN) {
    headers["Authorization"] = `Bearer ${INFERENCE_SERVICE_TOKEN}`;
  }

  const response = await fetch(`${INFERENCE_SERVICE_URL}/session-window/${sessionId}/stop`, {
    method: "POST",
    headers,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Failed to stop inference service: ${response.status} ${text}`);
  }
}
