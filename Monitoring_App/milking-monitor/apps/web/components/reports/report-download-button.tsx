"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { redirectOnApiError } from "../../lib/api/error";

export default function ReportDownloadButton({ sessionId }: { sessionId: string }) {
  const router = useRouter();
  const pathname = usePathname();
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
        const message = err?.error ?? "Download failed";
        if (redirectOnApiError((url) => router.push(url), response.status, message, pathname)) {
          return;
        }
        alert(message);
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
      const { buildErrorPageUrl } = await import("../../lib/api/error");
      router.push(
        buildErrorPageUrl({ status: 0, type: "network", message: "Could not reach the server. Check your connection." }, pathname),
      );
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
