import { describe, expect, it } from "vitest";
import { buildTaskEventFingerprint, isDuplicateTaskEvent } from "../data/event-dedupe";

describe("task event deduplication", () => {
  it("generates a stable fingerprint for the same event", () => {
    const input = {
      session_id: "11111111-1111-1111-1111-111111111111",
      cow_position: 1,
      task_id: "TASK-03",
      status: "completed",
      detected_start_time: "2026-09-22T10:00:00Z",
      detected_end_time: "2026-09-22T10:12:00Z",
    } as const;

    expect(buildTaskEventFingerprint(input)).toBe(buildTaskEventFingerprint(input));
    expect(buildTaskEventFingerprint(input)).toMatch(/^session:/);
  });

  it("detects duplicate task events with the same identity and timestamps", () => {
    const original = {
      session_id: "11111111-1111-1111-1111-111111111111",
      cow_position: 1,
      task_id: "TASK-03",
      status: "completed",
      detected_start_time: "2026-09-22T10:00:00Z",
      detected_end_time: "2026-09-22T10:12:00Z",
    } as const;

    const duplicate = {
      ...original,
      status: "completed",
      confidence_score: 0.91,
    };

    expect(isDuplicateTaskEvent(original, duplicate)).toBe(true);
    expect(isDuplicateTaskEvent(original, { ...original, task_id: "TASK-04" })).toBe(false);
  });
});
