ALTER TABLE "audit_log" ADD COLUMN "details" jsonb;--> statement-breakpoint
CREATE INDEX "audit_log_entity_created_at_idx" ON "audit_log" USING btree ("entity_type","entity_id","created_at");--> statement-breakpoint
CREATE INDEX "audit_log_actor_created_at_idx" ON "audit_log" USING btree ("actor_id","created_at");
--> statement-breakpoint
CREATE OR REPLACE FUNCTION prevent_audit_log_mutation() RETURNS trigger AS $$
BEGIN
	RAISE EXCEPTION 'audit_log records are immutable';
END;
$$ LANGUAGE plpgsql;
--> statement-breakpoint
CREATE TRIGGER audit_log_immutable_trigger
	BEFORE UPDATE OR DELETE ON "audit_log"
	FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation();