import { pgTable, uuid, text, timestamp } from "drizzle-orm/pg-core";

export const auditLogTable = "audit_log";

export const auditLog = pgTable(auditLogTable, {
  id: uuid("id").defaultRandom().primaryKey(),
  entity_type: text("entity_type").notNull(),
  entity_id: text("entity_id").notNull(),
  action: text("action").notNull(),
  actor_id: text("actor_id").notNull(),
  reason: text("reason"),
  created_at: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});
