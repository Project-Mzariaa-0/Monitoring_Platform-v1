export type InferenceHealth = {
  reachable: boolean;
  status: "ok" | "degraded" | "offline";
  ready: boolean;
  uptimeSeconds: number | null;
  activeSessions: string[];
  hybridEnabled: boolean | null;
  hybridReady: boolean | null;
  error?: string;
};

export async function getInferenceHealth(): Promise<InferenceHealth> {
  const inferenceUrl = process.env.INFERENCE_SERVICE_URL || "http://localhost:8001";

  try {
    const response = await fetch(`${inferenceUrl}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    if (!response.ok) {
      return {
        reachable: true,
        status: "degraded",
        ready: false,
        uptimeSeconds: null,
        activeSessions: [],
        hybridEnabled: null,
        hybridReady: null,
        error: `Health endpoint returned HTTP ${response.status}`,
      };
    }

    const payload = await response.json() as {
      status?: "ok" | "degraded";
      ready?: boolean;
      service?: {
        uptime_seconds?: number;
        active_sessions?: string[];
        hybrid_enabled?: boolean;
      };
    };

    return {
      reachable: true,
      status: payload.status ?? "degraded",
      ready: payload.ready === true,
      uptimeSeconds: payload.service?.uptime_seconds ?? null,
      activeSessions: payload.service?.active_sessions ?? [],
      hybridEnabled: payload.service?.hybrid_enabled ?? null,
      hybridReady: null,
    };
  } catch (error) {
    return {
      reachable: false,
      status: "offline",
      ready: false,
      uptimeSeconds: null,
      activeSessions: [],
      hybridEnabled: null,
      hybridReady: null,
      error: error instanceof Error ? error.message : "Inference service unavailable",
    };
  }
}

export function formatUptime(seconds: number | null): string {
  if (seconds === null) return "Unavailable";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}