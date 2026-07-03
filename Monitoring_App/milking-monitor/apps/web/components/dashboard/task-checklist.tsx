"use client";

import { useMemo, useState } from "react";
import OverrideModal from "./override-modal";
import { TASK_LABELS, TASK_ORDER } from "../../lib/constants";

type TaskEvent = {
  id: string;
  task_id: string;
  status: "completed" | "missed" | "anomaly_flagged" | "unverifiable";
  override_status?: "completed" | "missed" | "anomaly_flagged" | "unverifiable";
  duration_seconds: number;
  detected_start_time: string | null;
  detected_end_time: string | null;
};

type Props = {
  sessionId: string;
  taskEvents: TaskEvent[];
};

export default function TaskChecklist({ sessionId, taskEvents }: Props) {
  const [selectedTaskEvent, setSelectedTaskEvent] = useState<TaskEvent | null>(null);

  const rows = useMemo(() => {
    return TASK_ORDER.map((taskId) => {
      const event = taskEvents.find((item) => item.task_id === taskId) ?? null;
      const status = event?.override_status ?? event?.status ?? "pending";

      return {
        taskId,
        label: TASK_LABELS[taskId],
        event,
        status,
      };
    });
  }, [taskEvents]);

  return (
    <section className="card card-pad">
      <h2 className="section-title">Process Compliance Checklist</h2>
      <div className="page-grid">
        {rows.map((row) => (
          <div key={row.taskId} className="data-row">
            <div>
              <div style={{ fontWeight: 700 }}>{row.taskId}</div>
              <div className="muted" style={{ fontSize: 14 }}>
                {row.label}
              </div>
              <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                {row.event ? `${row.event.duration_seconds}s` : "No event recorded"}
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <span
                className={`status-pill ${
                  row.status === "completed"
                    ? "status-success"
                    : row.status === "missed" || row.status === "anomaly_flagged"
                      ? "status-danger"
                      : row.status === "unverifiable"
                        ? "status-warning"
                        : "status-neutral"
                }`}
              >
                {row.status}
              </span>
              <button
                className="button button-primary"
                type="button"
                disabled={!row.event}
                onClick={() => setSelectedTaskEvent(row.event)}
                style={{ opacity: row.event ? 1 : 0.5 }}
              >
                Override
              </button>
            </div>
          </div>
        ))}
      </div>

      <OverrideModal
        open={Boolean(selectedTaskEvent)}
        sessionId={sessionId}
        taskEvent={selectedTaskEvent}
        onClose={() => setSelectedTaskEvent(null)}
        onSaved={() => setSelectedTaskEvent(null)}
      />
    </section>
  );
}
