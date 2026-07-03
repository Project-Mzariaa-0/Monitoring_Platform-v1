"use client";

import { useMemo, useState } from "react";
import { useSession } from "next-auth/react";

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

  const summary = useMemo(
    () => [
      ["Start", scheduledStartTime || "Immediate"],
      ["End", estimatedEndTime || "One hour after start"],
      ["Herd", `${row1Count + row2Count} cows across two positions`],
      ["Operator", employeeName || "Not assigned"],
    ],
    [employeeName, estimatedEndTime, row1Count, row2Count, scheduledStartTime],
  );

  async function createSession() {
    const response = await fetch("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        supervisor_id: supervisorEmail || "anonymous",
        employee_id: employeeName || "unassigned",
        scheduled_start_time: scheduledStartTime || new Date().toISOString(),
        estimated_end_time: estimatedEndTime || new Date(Date.now() + 60 * 60 * 1000).toISOString(),
        employee_name: employeeName,
        supervisor_name: supervisorName,
        supervisor_email: supervisorEmail,
        row_1_cow_count: row1Count,
        row_2_cow_count: row2Count,
      }),
    });

    const payload = await response.json();
    setResult(response.ok ? `Session created: ${payload.data.id}` : payload.error ?? "Session creation failed");
  }

  function continueFlow() {
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
          <div>
            <label className="label">Scheduled start</label>
            <input className="input" type="datetime-local" value={scheduledStartTime} onChange={(event) => setScheduledStartTime(event.target.value)} />
          </div>
          <div>
            <label className="label">Estimated end</label>
            <input className="input" type="datetime-local" value={estimatedEndTime} onChange={(event) => setEstimatedEndTime(event.target.value)} />
          </div>
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
      {result ? <div className="status-tag status-success">{result}</div> : null}
    </div>
  );
}
