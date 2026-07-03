"use client";

import { useState } from "react";

export default function ReportGenerator({ sessionId }: { sessionId: string }) {
  const [status, setStatus] = useState<string | null>(null);

  async function generateReport() {
    const response = await fetch("/api/reports/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });

    const payload = await response.json();
    setStatus(response.ok ? `Report ready: ${payload.data.report.docx_file_url}` : payload.error ?? "Generation failed");
  }

  return (
    <div>
      <button className="button button-primary" type="button" onClick={generateReport}>
        Download Full Report (.docx)
      </button>
      {status ? (
        <div className="muted" style={{ marginTop: 12 }}>
          {status}
        </div>
      ) : null}
    </div>
  );
}
