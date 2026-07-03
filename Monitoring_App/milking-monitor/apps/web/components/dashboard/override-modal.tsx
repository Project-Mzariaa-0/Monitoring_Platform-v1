"use client";

import { useState } from "react";

type TaskEvent = {
  id: string;
  task_id: string;
  status: string;
  override_status?: string;
  duration_seconds: number;
};

type Props = {
  open: boolean;
  sessionId: string;
  taskEvent: TaskEvent | null;
  onClose: () => void;
  onSaved: () => void;
};

export default function OverrideModal({ open, sessionId, taskEvent, onClose, onSaved }: Props) {
  const [overrideStatus, setOverrideStatus] = useState<"completed" | "missed" | "anomaly_flagged" | "unverifiable">("unverifiable");
  const [reason, setReason] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const currentTaskEvent = open ? taskEvent : null;

  if (!currentTaskEvent) {
    return null;
  }

  const taskEventId = currentTaskEvent.id;
  const taskEventLabel = currentTaskEvent.task_id;
  const taskEventStatus = currentTaskEvent.override_status ?? currentTaskEvent.status;

  async function saveOverride() {
    const response = await fetch(`/api/task-events/${taskEventId}/override`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        override_status: overrideStatus,
        reason,
        actor_id: sessionId,
      }),
    });

    const payload = await response.json();
    if (response.ok) {
      setStatusMessage(`Saved override for ${payload.data.task_id}`);
      onSaved();
      return;
    }

    setStatusMessage(payload.error ?? "Override failed");
  }

  return (
    <div className="card card-pad" style={{ marginTop: 16, border: "1px solid var(--border)", background: "#fafafa" }}>
      <h2 className="section-title">Override task status</h2>
      <p className="muted">
        {taskEventLabel} · current status {taskEventStatus}
      </p>
      <div className="page-grid">
        <div>
          <label className="label">New status</label>
          <select className="select" value={overrideStatus} onChange={(event) => setOverrideStatus(event.target.value as typeof overrideStatus)}>
            <option value="completed">completed</option>
            <option value="missed">missed</option>
            <option value="anomaly_flagged">anomaly_flagged</option>
            <option value="unverifiable">unverifiable</option>
          </select>
        </div>
        <div>
          <label className="label">Reason</label>
          <textarea className="input" rows={3} value={reason} onChange={(event) => setReason(event.target.value)} />
        </div>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button className="button button-primary" type="button" onClick={saveOverride}>
            Save override
          </button>
          <button className="button button-secondary" type="button" onClick={onClose}>
            Close
          </button>
        </div>
        {statusMessage ? <div className="muted">{statusMessage}</div> : null}
      </div>
    </div>
  );
}
