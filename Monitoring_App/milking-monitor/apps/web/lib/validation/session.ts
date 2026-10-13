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
}).superRefine((value, context) => {
  const start = new Date(value.scheduled_start_time);
  const end = new Date(value.estimated_end_time);
  const now = Date.now();

  if (Number.isNaN(start.getTime())) {
    context.addIssue({ code: "custom", path: ["scheduled_start_time"], message: "Start time must be a valid date" });
  }
  if (Number.isNaN(end.getTime())) {
    context.addIssue({ code: "custom", path: ["estimated_end_time"], message: "End time must be a valid date" });
  }
  if (!Number.isNaN(start.getTime()) && start.getTime() < now - 60_000) {
    const moroccoNow = new Intl.DateTimeFormat("en-GB", {
      timeZone: "Africa/Casablanca",
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(now));
    context.addIssue({
      code: "custom",
      path: ["scheduled_start_time"],
      message: `Start time cannot be in the past (Morocco time now: ${moroccoNow}). If you picked 13:00 while it is already 14:xx in Morocco, that window is past due and will auto-complete.`,
    });
  }
  if (!Number.isNaN(start.getTime()) && !Number.isNaN(end.getTime()) && end <= start) {
    context.addIssue({ code: "custom", path: ["estimated_end_time"], message: "End time must be after the start time" });
  }
});

export const updateSessionEmployeeSchema = z.object({
  employee_id: z.string().min(1).max(255),
  employee_name: z.string().min(1).max(255),
});

export const sessionStatusEnum = z.enum(SESSION_STATUSES);

export type CreateSessionInput = z.infer<typeof createSessionSchema>;
export type UpdateSessionEmployeeInput = z.infer<typeof updateSessionEmployeeSchema>;
