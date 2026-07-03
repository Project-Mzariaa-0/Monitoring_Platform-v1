import { pgTable, uuid, text, timestamp, uniqueIndex } from "drizzle-orm/pg-core";

export const supervisorsTable = "supervisors";

export const supervisors = pgTable(
  supervisorsTable,
  {
    id: uuid("id").defaultRandom().primaryKey(),
    clerk_user_id: text("clerk_user_id").notNull(),
    name: text("name").notNull(),
    email: text("email").notNull(),
    created_at: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
    updated_at: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (table) => {
    return {
      clerkUserIdUnique: uniqueIndex("supervisors_clerk_user_id_unique").on(table.clerk_user_id),
      emailUnique: uniqueIndex("supervisors_email_unique").on(table.email),
    };
  }
);
