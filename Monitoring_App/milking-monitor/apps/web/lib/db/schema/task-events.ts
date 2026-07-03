import { pgTable, uuid, integer, timestamp, text } from "drizzle-orm/pg-core";
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

  override_status: text("override_status"),
  override_reason: text("override_reason"),
  overridden_by: text("overridden_by"),
  overridden_at: timestamp("overridden_at", { withTimezone: true }),

  created_at: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});
