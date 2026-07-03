import { z } from "zod";

const SESSION_STATUSES = ["scheduled", "active", "completed", "ended_early"] as const;

export const createSessionSchema = z.object({
  supervisor_id: z.string().min(1),
  employee_id: z.string().min(1),
  employee_name: z.string().min(1).max(255),
  supervisor_name: z.string().min(1).max(255),
  supervisor_email: z.string().min(1),
  scheduled_start_time: z.string().min(1),
  estimated_end_time: z.string().min(1),
  row_1_cow_count: z.coerce.number().int().min(1).max(50),
  row_2_cow_count: z.coerce.number().int().min(1).max(50),
});

export const updateSessionEmployeeSchema = z.object({
  employee_id: z.string().min(1).max(255),
  employee_name: z.string().min(1).max(255),
  actor_id: z.string().uuid(),
});

export const sessionStatusEnum = z.enum(SESSION_STATUSES);

export type CreateSessionInput = z.infer<typeof createSessionSchema>;
export type UpdateSessionEmployeeInput = z.infer<typeof updateSessionEmployeeSchema>;
