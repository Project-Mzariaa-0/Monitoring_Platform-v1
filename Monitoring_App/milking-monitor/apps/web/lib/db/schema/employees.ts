import { pgTable, uuid, text, timestamp, uniqueIndex } from "drizzle-orm/pg-core";
import { supervisors } from "./supervisors";

export const employeesTable = "employees";

export const employees = pgTable(
  employeesTable,
  {
    id: uuid("id").defaultRandom().primaryKey(),
    supervisor_id: uuid("supervisor_id").notNull().references(() => supervisors.id, { onDelete: "cascade" }),
    clerk_user_id: text("clerk_user_id"),
    employee_name: text("employee_name").notNull(),
    employee_email: text("employee_email"),
    created_at: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
    updated_at: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (table) => {
    return {
      clerkUserIdUnique: uniqueIndex("employees_clerk_user_id_unique").on(table.clerk_user_id),
      employeeEmailUnique: uniqueIndex("employees_employee_email_unique").on(table.employee_email),
    };
  }
);
