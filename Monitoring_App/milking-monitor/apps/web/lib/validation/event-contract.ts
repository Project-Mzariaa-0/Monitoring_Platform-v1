import { z } from "zod";

export const EVENT_CONTRACT_VERSION = "1.0" as const;

const taskIds = ["TASK-01", "TASK-02", "TASK-03", "TASK-04", "TASK-05", "TASK-06"] as const;
const taskStatuses = ["completed", "missed", "anomaly_flagged", "unverifiable"] as const;

const baseEventSchema = z.object({
  contract_version: z.literal(EVENT_CONTRACT_VERSION),
  session_id: z.string().uuid(),
});

export const taskEventContractSchema = baseEventSchema.extend({
  event_type: z.literal("task_event"),
  task_id: z.enum(taskIds),
  cow_position: z.union([z.literal(1), z.literal(2)]),
  status: z.enum(taskStatuses),
  confidence_score: z.number().min(0).max(1),
  completion_percentage: z.number().min(0).max(100),
  detected_start_time: z.string().datetime({ offset: true }),
  detected_end_time: z.string().datetime({ offset: true }).nullable(),
  duration_seconds: z.number().int().min(0),
}).strict();

export const cowProcessEventContractSchema = baseEventSchema.extend({
  event_type: z.literal("cow_process"),
  cow_position: z.union([z.literal(1), z.literal(2)]),
  process_status: z.enum(["started", "completed"]),
  detected_time: z.string().datetime({ offset: true }),
}).strict();

export const ingestEventContractSchema = z.discriminatedUnion("event_type", [
  taskEventContractSchema,
  cowProcessEventContractSchema,
]);

export type IngestEventContract = z.infer<typeof ingestEventContractSchema>;