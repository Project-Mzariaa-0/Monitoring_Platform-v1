export type TaskEventFingerprintInput = {
  session_id: string;
  cow_position: 1 | 2;
  task_id: string;
  status: string;
  detected_start_time?: string | null;
  detected_end_time?: string | null;
  duration_seconds?: number;
};

function normalizeDate(value?: string | null): string | null {
  if (!value) return null;

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value.trim();
  }

  return parsed.toISOString();
}

export function buildTaskEventFingerprint(input: TaskEventFingerprintInput): string {
  const normalizedStart = normalizeDate(input.detected_start_time);
  const normalizedEnd = normalizeDate(input.detected_end_time);
  const taskId = input.task_id.trim().toUpperCase();
  const status = input.status.trim().toLowerCase();
  const duration = Number.isFinite(input.duration_seconds) ? String(Math.round(input.duration_seconds ?? 0)) : "0";

  return [
    "session:",
    input.session_id,
    "|cow:",
    String(input.cow_position),
    "|task:",
    taskId,
    "|status:",
    status,
    "|start:",
    normalizedStart ?? "null",
    "|end:",
    normalizedEnd ?? "null",
    "|duration:",
    duration,
  ].join("");
}

export function isDuplicateTaskEvent(
  original: TaskEventFingerprintInput,
  candidate: TaskEventFingerprintInput,
): boolean {
  if (!original || !candidate) return false;

  return (
    original.session_id === candidate.session_id &&
    original.cow_position === candidate.cow_position &&
    original.task_id.trim().toUpperCase() === candidate.task_id.trim().toUpperCase() &&
    original.status.trim().toLowerCase() === candidate.status.trim().toLowerCase() &&
    normalizeDate(original.detected_start_time) === normalizeDate(candidate.detected_start_time) &&
    normalizeDate(original.detected_end_time) === normalizeDate(candidate.detected_end_time)
  );
}