import { z } from "zod";

const TASK_IDS = ["TASK-01", "TASK-02", "TASK-03", "TASK-04", "TASK-05", "TASK-06"] as const;
const TASK_STATUSES = ["completed", "missed", "anomaly_flagged", "unverifiable"] as const;

export const overrideTaskEventSchema = z.object({
  override_status: z.enum(TASK_STATUSES),
  reason: z.string().min(1).max(1000),
  actor_id: z.string().uuid(),
});

export const ingestTaskEventSchema = z.object({
  session_id: z.string().uuid(),
  cow_position: z.number().int().min(1).max(2),
  task_id: z.enum(TASK_IDS),
  status: z.enum(TASK_STATUSES),
  confidence_score: z.number().min(0).max(1).optional(),
  detected_start_time: z.string().datetime().nullable().optional(),
  detected_end_time: z.string().datetime().nullable().optional(),
  duration_seconds: z.number().int().min(0).optional(),
});

export const taskIdEnum = z.enum(TASK_IDS);
export const taskStatusEnum = z.enum(TASK_STATUSES);

export type OverrideTaskEventInput = z.infer<typeof overrideTaskEventSchema>;
export type IngestTaskEventInput = z.infer<typeof ingestTaskEventSchema>;
