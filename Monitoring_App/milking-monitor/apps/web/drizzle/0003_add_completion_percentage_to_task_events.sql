ALTER TABLE "task_events"
ADD COLUMN IF NOT EXISTS "completion_percentage" real NOT NULL DEFAULT 0;--> statement-breakpoint
