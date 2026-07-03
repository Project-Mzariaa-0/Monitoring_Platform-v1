import { pgTable, uuid, text, timestamp, integer } from "drizzle-orm/pg-core";

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
});
