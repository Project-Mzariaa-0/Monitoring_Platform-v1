ALTER TABLE "sessions" DROP CONSTRAINT "sessions_supervisor_id_supervisors_id_fk";
--> statement-breakpoint
ALTER TABLE "sessions" DROP CONSTRAINT "sessions_employee_id_employees_id_fk";
--> statement-breakpoint
ALTER TABLE "sessions" ALTER COLUMN "supervisor_id" SET DATA TYPE text;--> statement-breakpoint
ALTER TABLE "sessions" ALTER COLUMN "employee_id" SET DATA TYPE text;--> statement-breakpoint
ALTER TABLE "reports" ALTER COLUMN "docx_file_url" DROP NOT NULL;--> statement-breakpoint
ALTER TABLE "task_events" ADD COLUMN IF NOT EXISTS "completion_percentage" real DEFAULT 0 NOT NULL;--> statement-breakpoint
CREATE INDEX "sessions_status_scheduled_start_idx" ON "sessions" USING btree ("status","scheduled_start_time");--> statement-breakpoint
ALTER TABLE "sessions" ADD CONSTRAINT "sessions_status_check" CHECK ("sessions"."status" in ('scheduled', 'active', 'completed', 'ended_early'));--> statement-breakpoint
ALTER TABLE "sessions" ADD CONSTRAINT "sessions_cow_counts_check" CHECK ("sessions"."row_1_cow_count" >= 0 and "sessions"."row_2_cow_count" >= 0);--> statement-breakpoint
ALTER TABLE "sessions" ADD CONSTRAINT "sessions_time_order_check" CHECK ("sessions"."estimated_end_time" >= "sessions"."scheduled_start_time");