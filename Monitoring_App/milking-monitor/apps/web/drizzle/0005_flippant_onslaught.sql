CREATE UNIQUE INDEX "cow_processes_session_position_uidx" ON "cow_processes" USING btree ("session_id","cow_position");--> statement-breakpoint
CREATE INDEX "task_events_cow_process_created_at_idx" ON "task_events" USING btree ("cow_process_id","created_at");--> statement-breakpoint
CREATE INDEX "task_events_task_status_idx" ON "task_events" USING btree ("task_id","status");--> statement-breakpoint
ALTER TABLE "cow_processes" ADD CONSTRAINT "cow_processes_position_check" CHECK ("cow_processes"."cow_position" in (1, 2));--> statement-breakpoint
ALTER TABLE "cow_processes" ADD CONSTRAINT "cow_processes_status_check" CHECK ("cow_processes"."overall_status" in ('in_progress', 'completed', 'completed_with_missed_tasks'));--> statement-breakpoint
ALTER TABLE "cow_processes" ADD CONSTRAINT "cow_processes_time_order_check" CHECK ("cow_processes"."detected_end_time" is null or "cow_processes"."detected_start_time" is null or "cow_processes"."detected_end_time" >= "cow_processes"."detected_start_time");--> statement-breakpoint
ALTER TABLE "task_events" ADD CONSTRAINT "task_events_task_id_check" CHECK ("task_events"."task_id" in ('TASK-01', 'TASK-02', 'TASK-03', 'TASK-04', 'TASK-05', 'TASK-06'));--> statement-breakpoint
ALTER TABLE "task_events" ADD CONSTRAINT "task_events_status_check" CHECK ("task_events"."status" in ('completed', 'missed', 'anomaly_flagged', 'unverifiable'));--> statement-breakpoint
ALTER TABLE "task_events" ADD CONSTRAINT "task_events_duration_check" CHECK ("task_events"."duration_seconds" >= 0);--> statement-breakpoint
ALTER TABLE "task_events" ADD CONSTRAINT "task_events_completion_check" CHECK ("task_events"."completion_percentage" >= 0 and "task_events"."completion_percentage" <= 100);--> statement-breakpoint
ALTER TABLE "task_events" ADD CONSTRAINT "task_events_time_order_check" CHECK ("task_events"."detected_end_time" is null or "task_events"."detected_start_time" is null or "task_events"."detected_end_time" >= "task_events"."detected_start_time");