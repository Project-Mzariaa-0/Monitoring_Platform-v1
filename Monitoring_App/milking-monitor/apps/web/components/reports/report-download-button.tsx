"use client";

import { useState } from "react";

export default function ReportDownloadButton({ sessionId }: { sessionId: string }) {
  const [loading, setLoading] = useState(false);

  async function download() {
    setLoading(true);
    try {
      const response = await fetch("/api/reports/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => null);
        alert(err?.error ?? "Download failed");
        return;
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `milking-report-${sessionId.slice(0, 8)}.docx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      alert("Download failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <button className="button button-secondary" type="button" onClick={download} disabled={loading}>
      {loading ? "Generating..." : "Download"}
    </button>
  );
}
