import { pgTable, uuid, text, timestamp, jsonb, index } from "drizzle-orm/pg-core";

export const auditLogTable = "audit_log";

export const auditLog = pgTable(auditLogTable, {
  id: uuid("id").defaultRandom().primaryKey(),
  entity_type: text("entity_type").notNull(),
  entity_id: text("entity_id").notNull(),
  action: text("action").notNull(),
  actor_id: text("actor_id").notNull(),
  reason: text("reason"),
  details: jsonb("details"),
  created_at: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (table) => [
  index("audit_log_entity_created_at_idx").on(table.entity_type, table.entity_id, table.created_at),
  index("audit_log_actor_created_at_idx").on(table.actor_id, table.created_at),
]);
