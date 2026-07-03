CREATE TABLE "audit_log" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"entity_type" text NOT NULL,
	"entity_id" text NOT NULL,
	"action" text NOT NULL,
	"actor_id" text NOT NULL,
	"reason" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "cow_processes" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"session_id" uuid NOT NULL,
	"cow_position" integer NOT NULL,
	"detected_start_time" timestamp with time zone,
	"detected_end_time" timestamp with time zone,
	"overall_status" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "employees" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"supervisor_id" uuid NOT NULL,
	"clerk_user_id" text,
	"employee_name" text NOT NULL,
	"employee_email" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "reports" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"session_id" uuid NOT NULL,
	"generated_at" timestamp with time zone NOT NULL,
	"docx_file_url" text NOT NULL,
	"email_sent_at" timestamp with time zone,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "sessions" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"supervisor_id" uuid NOT NULL,
	"employee_id" uuid NOT NULL,
	"employee_name" text NOT NULL,
	"supervisor_name" text NOT NULL,
	"supervisor_email" text NOT NULL,
	"scheduled_start_time" timestamp with time zone NOT NULL,
	"estimated_end_time" timestamp with time zone NOT NULL,
	"actual_end_time" timestamp with time zone,
	"row_1_cow_count" integer NOT NULL,
	"row_2_cow_count" integer NOT NULL,
	"status" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "supervisors" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"clerk_user_id" text NOT NULL,
	"name" text NOT NULL,
	"email" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "task_events" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"cow_process_id" uuid NOT NULL,
	"task_id" text NOT NULL,
	"detected_start_time" timestamp with time zone,
	"detected_end_time" timestamp with time zone,
	"duration_seconds" integer NOT NULL,
	"status" text NOT NULL,
	"override_status" text,
	"override_reason" text,
	"overridden_by" text,
	"overridden_at" timestamp with time zone,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX "employees_clerk_user_id_unique" ON "employees" USING btree ("clerk_user_id");--> statement-breakpoint
CREATE UNIQUE INDEX "employees_employee_email_unique" ON "employees" USING btree ("employee_email");--> statement-breakpoint
CREATE UNIQUE INDEX "supervisors_clerk_user_id_unique" ON "supervisors" USING btree ("clerk_user_id");--> statement-breakpoint
CREATE UNIQUE INDEX "supervisors_email_unique" ON "supervisors" USING btree ("email");