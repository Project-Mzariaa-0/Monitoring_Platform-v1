import { pgTable, uuid, integer, timestamp, text, check, index, uniqueIndex } from "drizzle-orm/pg-core";
import { sql } from "drizzle-orm";
import { sessions } from "./sessions";

export const cowProcessesTable = "cow_processes";

export const cowProcesses = pgTable(cowProcessesTable, {
  id: uuid("id").defaultRandom().primaryKey(),
  session_id: uuid("session_id").notNull().references(() => sessions.id, { onDelete: "cascade" }),

  cow_position: integer("cow_position").notNull(), // 1 | 2
  detected_start_time: timestamp("detected_start_time", { withTimezone: true }),
  detected_end_time: timestamp("detected_end_time", { withTimezone: true }),

  overall_status: text("overall_status").notNull(), // in_progress | completed | completed_with_missed_tasks

  created_at: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updated_at: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
}, (table) => [
  uniqueIndex("cow_processes_session_position_uidx").on(table.session_id, table.cow_position),
  check("cow_processes_position_check", sql`${table.cow_position} in (1, 2)`),
  check("cow_processes_status_check", sql`${table.overall_status} in ('in_progress', 'completed', 'completed_with_missed_tasks')`),
  check("cow_processes_time_order_check", sql`${table.detected_end_time} is null or ${table.detected_start_time} is null or ${table.detected_end_time} >= ${table.detected_start_time}`),
]);
