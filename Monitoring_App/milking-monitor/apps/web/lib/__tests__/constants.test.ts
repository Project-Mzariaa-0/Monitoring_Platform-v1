import { describe, it, expect } from "vitest";
import {
  TASK_IDS,
  TASK_LABELS,
  TASK_ORDER,
  COMPLIANCE_BASE_SCORE,
  COMPLIANCE_MISSED_PENALTY,
  complianceScore,
  complianceLabel,
  formatDuration,
} from "../constants";

describe("TASK_IDS", () => {
  it("contains exactly 6 task IDs", () => {
    expect(TASK_IDS).toHaveLength(6);
  });

  it("each task ID follows TASK-XX format", () => {
    for (const id of TASK_IDS) {
      expect(id).toMatch(/^TASK-\d{2}$/);
    }
  });
});

describe("TASK_LABELS", () => {
  it("has a label for every task ID", () => {
    for (const id of TASK_IDS) {
      expect(TASK_LABELS[id]).toBeDefined();
      expect(typeof TASK_LABELS[id]).toBe("string");
      expect(TASK_LABELS[id].length).toBeGreaterThan(0);
    }
  });
});

describe("TASK_ORDER", () => {
  it("matches TASK_IDS", () => {
    expect(TASK_ORDER).toEqual([...TASK_IDS]);
  });
});

describe("complianceScore", () => {
  it("returns base score when no tasks missed", () => {
    expect(complianceScore(0)).toBe(COMPLIANCE_BASE_SCORE);
  });

  it("decreases by penalty per missed task", () => {
    expect(complianceScore(1)).toBe(COMPLIANCE_BASE_SCORE - COMPLIANCE_MISSED_PENALTY);
    expect(complianceScore(2)).toBe(COMPLIANCE_BASE_SCORE - 2 * COMPLIANCE_MISSED_PENALTY);
  });

  it("never goes below 0", () => {
    expect(complianceScore(100)).toBe(0);
    expect(complianceScore(999)).toBe(0);
  });

  it("never goes above 100", () => {
    expect(complianceScore(-1)).toBeLessThanOrEqual(100);
    expect(complianceScore(-100)).toBeLessThanOrEqual(100);
  });
});

describe("complianceLabel", () => {
  it("returns Optimal for scores >= 90", () => {
    expect(complianceLabel(100)).toBe("Optimal");
    expect(complianceLabel(90)).toBe("Optimal");
    expect(complianceLabel(95)).toBe("Optimal");
  });

  it("returns At Risk for scores 75-89", () => {
    expect(complianceLabel(89)).toBe("At Risk");
    expect(complianceLabel(75)).toBe("At Risk");
    expect(complianceLabel(80)).toBe("At Risk");
  });

  it("returns Critical for scores < 75", () => {
    expect(complianceLabel(74)).toBe("Critical");
    expect(complianceLabel(0)).toBe("Critical");
  });
});

describe("formatDuration", () => {
  it("returns 0s for zero or negative", () => {
    expect(formatDuration(0)).toBe("0s");
    expect(formatDuration(-5)).toBe("0s");
  });

  it("formats seconds only", () => {
    expect(formatDuration(30)).toBe("30s");
    expect(formatDuration(59)).toBe("59s");
  });

  it("formats minutes and seconds", () => {
    expect(formatDuration(60)).toBe("1m 0s");
    expect(formatDuration(90)).toBe("1m 30s");
    expect(formatDuration(125)).toBe("2m 5s");
  });
});
