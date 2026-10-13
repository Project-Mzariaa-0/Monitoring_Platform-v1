"use client";

import { useEffect, useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import {
  MOROCCO_TIME_ZONE,
  formatInMorocco,
  moroccoDateTimeInputToIso,
  nowMoroccoInput,
} from "../../../lib/time/morocco";

const steps = ["Timing", "Herd Details", "Assignment", "Review"];

export default function MultiStepSessionForm() {
  const { data: session } = useSession();
  const [activeStep, setActiveStep] = useState(0);
  const [scheduledStartTime, setScheduledStartTime] = useState("");
  const [estimatedEndTime, setEstimatedEndTime] = useState("");
  const [row1Count, setRow1Count] = useState(12);
  const [row2Count, setRow2Count] = useState(12);
  const [employeeName, setEmployeeName] = useState("");
  const [supervisorName, setSupervisorName] = useState(session?.user?.name || "");
  const [supervisorEmail, setSupervisorEmail] = useState(session?.user?.email || "");
  const [result, setResult] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [moroccoNow, setMoroccoNow] = useState(() => nowMoroccoInput());
  const [moroccoNowLabel, setMoroccoNowLabel] = useState(() => formatInMorocco(new Date().toISOString()));
  const [nowMs, setNowMs] = useState<number>(() => Date.now());
  const [serverSkewMs, setServerSkewMs] = useState<number | null>(null);
  const [timeSource, setTimeSource] = useState<"server" | "device">("device");

  useEffect(() => {
    let cancelled = false;
    const sync = async () => {
      const tick = Date.now();
      try {
        const res = await fetch("/api/time", { cache: "no-store" });
        const payload = await res.json().catch(() => null);
        const serverUtc = payload?.data?.nowUtc as string | undefined;
        if (!cancelled && serverUtc) {
          const ms = new Date(serverUtc).getTime();
          if (!Number.isNaN(ms)) {
            setServerSkewMs(ms - tick);
            setNowMs(tick);
            setMoroccoNow(payload.data.nowMoroccoInput ?? nowMoroccoInput());
            setMoroccoNowLabel(payload.data.nowMoroccoLabel ?? formatInMorocco(serverUtc));
            setTimeSource("server");
            return;
          }
        }
      } catch {
        // fall back to device clock
      }
      if (!cancelled) {
        setServerSkewMs(null);
        setNowMs(tick);
        setMoroccoNow(nowMoroccoInput());
        setMoroccoNowLabel(formatInMorocco(new Date().toISOString()));
        setTimeSource("device");
      }
    };
    void sync();
    const id = window.setInterval(sync, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const minStart = useMemo(() => moroccoNow.slice(0, 16), [moroccoNow]);

  const timingError = useMemo(() => {
    if (!scheduledStartTime || !estimatedEndTime) return null;
    try {
      const start = new Date(moroccoDateTimeInputToIso(scheduledStartTime)).getTime();
      const end = new Date(moroccoDateTimeInputToIso(estimatedEndTime)).getTime();
      if (Number.isNaN(start) || Number.isNaN(end)) return "Enter valid start and end times.";
      if (end <= start) return "End time must be after the start time (Morocco time).";
      const referenceNow = nowMs + (serverSkewMs ?? 0);
      if (start < referenceNow - 60_000) {
        return `Start time is in the past. Current Morocco time is ${moroccoNowLabel} — pick a time at or after now.`;
      }
      return null;
    } catch {
      return null;
    }
  }, [scheduledStartTime, estimatedEndTime, moroccoNowLabel, nowMs, serverSkewMs]);

  const summary = useMemo(
    () => [
      ["Start", scheduledStartTime ? `${scheduledStartTime.replace("T", " ")} (Morocco)` : "Immediate"],
      ["End", estimatedEndTime ? `${estimatedEndTime.replace("T", " ")} (Morocco)` : "One hour after start"],
      ["Herd", `${row1Count + row2Count} cows across two positions`],
      ["Operator", employeeName || "Not assigned"],
    ],
    [employeeName, estimatedEndTime, row1Count, row2Count, scheduledStartTime],
  );

  async function createSession() {
    setFormError(null);
    if (timingError) {
      setFormError(timingError);
      setActiveStep(0);
      return;
    }
    let response: Response;
    try {
      response = await fetch("/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          supervisor_id: supervisorEmail || "anonymous",
          employee_id: employeeName || "unassigned",
          scheduled_start_time: scheduledStartTime ? moroccoDateTimeInputToIso(scheduledStartTime) : new Date().toISOString(),
          estimated_end_time: estimatedEndTime ? moroccoDateTimeInputToIso(estimatedEndTime) : new Date(Date.now() + 60 * 60 * 1000).toISOString(),
          employee_name: employeeName,
          supervisor_name: supervisorName,
          supervisor_email: supervisorEmail,
          row_1_cow_count: row1Count,
          row_2_cow_count: row2Count,
        }),
      });
    } catch {
      const { buildErrorPageUrl } = await import("../../../lib/api/error");
      window.location.assign(
        buildErrorPageUrl({ status: 0, type: "network", message: "Could not reach the server. Check your connection." }, "/scheduler/new"),
      );
      return;
    }

    const payload = await response.json().catch(() => null);
    if (response.ok) {
      setResult(`Session created: ${payload?.data?.id ?? "ok"}`);
    } else {
      const details = payload?.details
        ? Object.entries(payload.details as Record<string, string[]>)
            .map(([field, messages]) => `${field}: ${(messages ?? []).join(", ")}`)
            .join(" | ")
        : null;
      const message = details ? `${payload?.error ?? "Session creation failed"} — ${details}` : (payload?.error ?? "Session creation failed");
      const { redirectOnApiError } = await import("../../../lib/api/error");
      if (redirectOnApiError((url: string) => window.location.assign(url), response.status, message, "/scheduler/new")) {
        return;
      }
      setResult(null);
      setFormError(message);
    }
  }

  function continueFlow() {
    if (activeStep === 0 && timingError) {
      setFormError(timingError);
      return;
    }
    if (activeStep < steps.length - 1) {
      setActiveStep((current) => current + 1);
      return;
    }
    void createSession();
  }

  return (
    <div className="page-grid">
      <div style={{ position: "relative", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 12 }}>
        {steps.map((step, index) => (
          <button
            key={step}
            className="button button-secondary"
            type="button"
            onClick={() => setActiveStep(index)}
            style={{
              borderRadius: 999,
              background: index === activeStep ? "var(--primary-button-bg)" : "#fff",
              color: index === activeStep ? "#fff" : "var(--text-primary)",
            }}
          >
            <span
              style={{
                width: 24,
                height: 24,
                display: "grid",
                placeItems: "center",
                borderRadius: 999,
                background: index === activeStep ? "var(--accent)" : "var(--neutral-soft)",
                color: "var(--sidebar-bg)",
              }}
            >
              {index + 1}
            </span>
            {step}
          </button>
        ))}
      </div>

      {activeStep === 0 ? (
        <div className="grid-2">
          <div className="card card-pad" style={{ gridColumn: "1 / -1", borderLeft: "4px solid var(--accent)" }}>
            Current Morocco time ({MOROCCO_TIME_ZONE}): <strong>{moroccoNowLabel}</strong>
            <span className="muted" style={{ fontSize: 12, marginLeft: 8 }}>
              ({timeSource === "server" ? "server time — use this even if your PC clock differs" : "device time — syncing with server..."})
            </span>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              All times below are Morocco wall time. If your device shows 13:47 while this banner shows 14:47,
              trust this banner — picking 13:xx now is in the past and will instantly auto-complete.
            </div>
          </div>
          <div>
            <label className="label">Scheduled start (Morocco time)</label>
            <input
              className="input"
              type="datetime-local"
              value={scheduledStartTime}
              min={minStart}
              onChange={(event) => setScheduledStartTime(event.target.value)}
            />
          </div>
          <div>
            <label className="label">Estimated end (Morocco time)</label>
            <input
              className="input"
              type="datetime-local"
              value={estimatedEndTime}
              min={scheduledStartTime || minStart}
              onChange={(event) => setEstimatedEndTime(event.target.value)}
            />
          </div>
          {timingError ? (
            <div className="status-tag status-danger" style={{ gridColumn: "1 / -1" }}>
              {timingError}
            </div>
          ) : null}
          <div className="card card-pad" style={{ gridColumn: "1 / -1", borderLeft: "4px solid var(--accent)" }}>
            Buffer windows are applied before and after the session so camera initialization and cleanup events remain auditable.
          </div>
        </div>
      ) : null}

      {activeStep === 1 ? (
        <div className="grid-2">
          <div>
            <label className="label">Position 1 cow count</label>
            <input className="input" type="number" value={row1Count} onChange={(event) => setRow1Count(Number(event.target.value))} />
          </div>
          <div>
            <label className="label">Position 2 cow count</label>
            <input className="input" type="number" value={row2Count} onChange={(event) => setRow2Count(Number(event.target.value))} />
          </div>
        </div>
      ) : null}

      {activeStep === 2 ? (
        <div className="grid-2">
          <div>
            <label className="label">Operator name</label>
            <input className="input" value={employeeName} onChange={(event) => setEmployeeName(event.target.value)} placeholder="Enter operator name" />
          </div>
          <div>
            <label className="label">Supervisor name</label>
            <input className="input" value={supervisorName} onChange={(event) => setSupervisorName(event.target.value)} />
          </div>
          <div>
            <label className="label">Supervisor email</label>
            <input className="input" type="email" value={supervisorEmail} onChange={(event) => setSupervisorEmail(event.target.value)} />
          </div>
        </div>
      ) : null}

      {activeStep === 3 ? (
        <div className="card card-pad">
          <h2 className="section-title">Review</h2>
          {summary.map(([label, value]) => (
            <div className="data-row" key={label}>
              <span className="muted">{label}</span>
              <strong>{value}</strong>
            </div>
          ))}
          {timingError ? <div className="status-tag status-danger" style={{ marginTop: 12 }}>{timingError}</div> : null}
        </div>
      ) : null}

      <div style={{ display: "flex", justifyContent: "flex-end", gap: 12 }}>
        {activeStep > 0 ? (
          <button className="button button-secondary" type="button" onClick={() => setActiveStep((current) => current - 1)}>
            Back
          </button>
        ) : null}
        <button className="button button-primary" type="button" onClick={continueFlow}>
          {activeStep === steps.length - 1 ? "Confirm Session" : "Continue ->"}
        </button>
      </div>
      {formError ? <div className="status-tag status-danger">{formError}</div> : null}
      {result ? <div className="status-tag status-success">{result}</div> : null}
    </div>
  );
}
