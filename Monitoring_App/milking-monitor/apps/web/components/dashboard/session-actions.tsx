"use client";

import { useState } from "react";

type Props = {
  sessionId: string;
  employeeName: string;
  supervisorName: string;
  supervisorEmail: string;
};

export default function SessionActions({ sessionId, employeeName, supervisorName, supervisorEmail }: Props) {
  const [nextEmployeeName, setNextEmployeeName] = useState(employeeName);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  async function handleUpdateEmployee() {
    const response = await fetch(`/api/sessions/${sessionId}/employee`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        employee_id: nextEmployeeName.toLowerCase().replace(/\s+/g, "-"),
        employee_name: nextEmployeeName,
        actor_id: supervisorName,
      }),
    });

    const payload = await response.json();
    setStatusMessage(response.ok ? `Employee updated to ${payload.data.employee_name}` : payload.error ?? "Update failed");
  }

  return (
    <div className="page-grid" style={{ marginTop: 16 }}>
      <div>
        <label className="label">Employee name</label>
        <input className="input" value={nextEmployeeName} onChange={(event) => setNextEmployeeName(event.target.value)} />
      </div>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <button className="button button-primary" type="button" onClick={handleUpdateEmployee}>
          Save employee update
        </button>
        <span className="muted" style={{ alignSelf: "center", fontSize: 14 }}>
          {supervisorEmail}
        </span>
      </div>
      {statusMessage ? <div className="muted">{statusMessage}</div> : null}
    </div>
  );
}