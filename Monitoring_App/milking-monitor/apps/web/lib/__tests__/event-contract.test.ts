import { describe, expect, it } from "vitest";
import { ingestEventContractSchema } from "../validation/event-contract";

const sessionId = "11111111-1111-4111-8111-111111111111";

const taskEvent = {
  contract_version: "1.0",
  session_id: sessionId,
  event_type: "task_event",
  task_id: "TASK-03",
  cow_position: 1,
  status: "completed",
  confidence_score: 0.94,
  completion_percentage: 100,
  detected_start_time: "2026-09-22T10:00:00Z",
  detected_end_time: "2026-09-22T10:00:10Z",
  duration_seconds: 10,
};

describe("ingest event contract", () => {
  it("accepts a versioned task event", () => {
    expect(ingestEventContractSchema.safeParse(taskEvent).success).toBe(true);
  });

  it("rejects unknown fields", () => {
    expect(ingestEventContractSchema.safeParse({ ...taskEvent, unexpected: true }).success).toBe(false);
  });

  it("rejects unsupported contract versions", () => {
    expect(ingestEventContractSchema.safeParse({ ...taskEvent, contract_version: "2.0" }).success).toBe(false);
  });
});
