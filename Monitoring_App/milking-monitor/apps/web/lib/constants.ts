export const TASK_IDS = ["TASK-01", "TASK-02", "TASK-03", "TASK-04", "TASK-05", "TASK-06"] as const;

export const TASK_LABELS: Record<string, string> = {
  "TASK-01": "Pre-cleaning",
  "TASK-02": "Stripping",
  "TASK-03": "Machine attachment",
  "TASK-04": "Milking",
  "TASK-05": "Detachment",
  "TASK-06": "Post-dip",
};

export const TASK_ORDER = [...TASK_IDS];

export const COMPLIANCE_BASE_SCORE = 96;
export const COMPLIANCE_MISSED_PENALTY = 3;
export const COMPLIANCE_ANALYTICS_PENALTY = 2;

export function complianceScore(missedCount: number): number {
  return Math.max(0, Math.min(100, COMPLIANCE_BASE_SCORE - missedCount * COMPLIANCE_MISSED_PENALTY));
}

export function complianceLabel(score: number): string {
  if (score >= 90) return "Optimal";
  if (score >= 75) return "At Risk";
  return "Critical";
}

export function formatDuration(seconds: number): string {
  if (seconds <= 0) return "0s";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}
