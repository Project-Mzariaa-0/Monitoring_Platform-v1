import { pgTable, uuid, text, timestamp, integer, check, index } from "drizzle-orm/pg-core";
import { sql } from "drizzle-orm";

export const sessionsTable = "sessions";

export const sessions = pgTable(sessionsTable, {
  id: uuid("id").defaultRandom().primaryKey(),
  supervisor_id: text("supervisor_id").notNull(),
  employee_id: text("employee_id").notNull(),

  employee_name: text("employee_name").notNull(),
  supervisor_name: text("supervisor_name").notNull(),
  supervisor_email: text("supervisor_email").notNull(),

  scheduled_start_time: timestamp("scheduled_start_time", { withTimezone: true }).notNull(),
  estimated_end_time: timestamp("estimated_end_time", { withTimezone: true }).notNull(),
  actual_end_time: timestamp("actual_end_time", { withTimezone: true }),

  row_1_cow_count: integer("row_1_cow_count").notNull(),
  row_2_cow_count: integer("row_2_cow_count").notNull(),

  status: text("status").notNull(), // e.g. scheduled | active | completed | ended_early

  created_at: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updated_at: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
}, (table) => [
  check("sessions_status_check", sql`${table.status} in ('scheduled', 'active', 'completed', 'ended_early')`),
  check("sessions_cow_counts_check", sql`${table.row_1_cow_count} >= 0 and ${table.row_2_cow_count} >= 0`),
  check("sessions_time_order_check", sql`${table.estimated_end_time} >= ${table.scheduled_start_time}`),
  index("sessions_status_scheduled_start_idx").on(table.status, table.scheduled_start_time),
]);
