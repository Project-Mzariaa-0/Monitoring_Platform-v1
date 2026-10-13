import { pgTable, uuid, integer, timestamp, text, real, check, index } from "drizzle-orm/pg-core";
import { sql } from "drizzle-orm";
import { cowProcesses } from "./cow-processes";

export const taskEventsTable = "task_events";

export const taskEvents = pgTable(taskEventsTable, {
  id: uuid("id").defaultRandom().primaryKey(),
  cow_process_id: uuid("cow_process_id").notNull().references(() => cowProcesses.id, { onDelete: "cascade" }),

  task_id: text("task_id").notNull(), // TASK-01..TASK-06
  detected_start_time: timestamp("detected_start_time", { withTimezone: true }),
  detected_end_time: timestamp("detected_end_time", { withTimezone: true }),

  duration_seconds: integer("duration_seconds").notNull(),
  status: text("status").notNull(), // completed | missed | anomaly_flagged | unverifiable
  confidence_score: real("confidence_score").notNull().default(0),
  completion_percentage: real("completion_percentage").notNull().default(0),

  override_status: text("override_status"),
  override_reason: text("override_reason"),
  overridden_by: text("overridden_by"),
  overridden_at: timestamp("overridden_at", { withTimezone: true }),

  created_at: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (table) => [
  index("task_events_cow_process_created_at_idx").on(table.cow_process_id, table.created_at),
  index("task_events_task_status_idx").on(table.task_id, table.status),
  check("task_events_task_id_check", sql`${table.task_id} in ('TASK-01', 'TASK-02', 'TASK-03', 'TASK-04', 'TASK-05', 'TASK-06')`),
  check("task_events_status_check", sql`${table.status} in ('completed', 'missed', 'anomaly_flagged', 'unverifiable')`),
  check("task_events_duration_check", sql`${table.duration_seconds} >= 0`),
  check("task_events_completion_check", sql`${table.completion_percentage} >= 0 and ${table.completion_percentage} <= 100`),
  check("task_events_time_order_check", sql`${table.detected_end_time} is null or ${table.detected_start_time} is null or ${table.detected_end_time} >= ${table.detected_start_time}`),
]);
