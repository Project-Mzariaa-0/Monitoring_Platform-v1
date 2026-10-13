"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";

type Props = {
  sessionId: string;
  employeeName: string;
  supervisorName: string;
  supervisorEmail: string;
};

export default function SessionActions({ sessionId, employeeName, supervisorName, supervisorEmail }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const [nextEmployeeName, setNextEmployeeName] = useState(employeeName);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  async function handleUpdateEmployee() {
    let response: Response;
    try {
      response = await fetch(`/api/sessions/${sessionId}/employee`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          employee_id: nextEmployeeName.toLowerCase().replace(/\s+/g, "-"),
          employee_name: nextEmployeeName,
        }),
      });
    } catch {
      const { buildErrorPageUrl } = await import("../../lib/api/error");
      router.push(
        buildErrorPageUrl({ status: 0, type: "network", message: "Could not reach the server. Check your connection." }, pathname),
      );
      return;
    }

    if (!response.ok) {
      const { buildErrorPageUrl, shouldRedirectToErrorPage, typeForStatus } = await import("../../lib/api/error");
      const payload = await response.json().catch(() => null);
      if (shouldRedirectToErrorPage(response.status)) {
        router.push(
          buildErrorPageUrl(
            {
              status: response.status,
              type: typeForStatus(response.status),
              message: (payload as { error?: string } | null)?.error ?? "Update failed",
            },
            pathname,
          ),
        );
        return;
      }
      setStatusMessage((payload as { error?: string } | null)?.error ?? "Update failed");
      return;
    }

    const payload = await response.json();
    setStatusMessage(`Employee updated to ${payload.data.employee_name}`);
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