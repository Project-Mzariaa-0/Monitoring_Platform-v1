"use client";

import { useEffect, useRef, useState } from "react";

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
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  const currentTaskEvent = open ? taskEvent : null;

  useEffect(() => {
    if (open) {
      previousFocusRef.current = document.activeElement as HTMLElement;
      dialogRef.current?.focus();
    } else {
      previousFocusRef.current?.focus();
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
      }
      if (e.key === "Tab" && dialogRef.current) {
        const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

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
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(31, 77, 58, 0.18)",
        backdropFilter: "blur(2px)",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="override-dialog-title"
        tabIndex={-1}
        style={{
          width: "min(100%, 480px)",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-card)",
          boxShadow: "var(--shadow-elevated)",
          padding: 24,
          outline: "none",
        }}
      >
        <h2 id="override-dialog-title" className="section-title" style={{ marginBottom: 4 }}>
          Override task status
        </h2>
        <p className="muted" style={{ margin: "0 0 20px" }}>
          {taskEventLabel} · current status {taskEventStatus}
        </p>
        <div style={{ display: "grid", gap: 16 }}>
          <div>
            <label className="label" htmlFor="override-status">New status</label>
            <select
              id="override-status"
              className="select"
              value={overrideStatus}
              onChange={(event) => setOverrideStatus(event.target.value as typeof overrideStatus)}
            >
              <option value="completed">completed</option>
              <option value="missed">missed</option>
              <option value="anomaly_flagged">anomaly_flagged</option>
              <option value="unverifiable">unverifiable</option>
            </select>
          </div>
          <div>
            <label className="label" htmlFor="override-reason">Reason</label>
            <textarea
              id="override-reason"
              className="input"
              rows={3}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
          </div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <button className="button button-primary" type="button" onClick={saveOverride}>
              Save override
            </button>
            <button className="button button-secondary" type="button" onClick={onClose}>
              Cancel
            </button>
          </div>
          {statusMessage ? <div className="muted">{statusMessage}</div> : null}
        </div>
      </div>
    </div>
  );
}
