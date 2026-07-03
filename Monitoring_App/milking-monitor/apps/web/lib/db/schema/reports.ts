import { pgTable, uuid, timestamp, text } from "drizzle-orm/pg-core";
import { sessions } from "./sessions";

export const reportsTable = "reports";

export const reports = pgTable(reportsTable, {
  id: uuid("id").defaultRandom().primaryKey(),
  session_id: uuid("session_id").notNull().references(() => sessions.id, { onDelete: "cascade" }),
  generated_at: timestamp("generated_at", { withTimezone: true }).notNull(),

  docx_file_url: text("docx_file_url").notNull(),
  email_sent_at: timestamp("email_sent_at", { withTimezone: true }),

  created_at: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updated_at: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});
