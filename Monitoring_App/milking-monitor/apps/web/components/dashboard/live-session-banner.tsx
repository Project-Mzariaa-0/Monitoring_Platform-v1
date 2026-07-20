"use client";

import { useEffect, useState } from "react";

function formatDuration(startTime: string, endTime: string): string {
  const diff = Math.floor((new Date(endTime).getTime() - new Date(startTime).getTime()) / 1000);
  if (diff <= 0) return "--:--";
  const m = Math.floor(diff / 60);
  const s = diff % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function LiveSessionBanner({
  sessionId,
  operator,
  active = true,
  scheduledStart,
  estimatedEnd,
  cowCount,
}: {
  sessionId?: string;
  operator?: string;
  active?: boolean;
  scheduledStart?: string;
  estimatedEnd?: string;
  cowCount?: number;
}) {
  const [now, setNow] = useState(0);

  useEffect(() => {
    if (!active) return;
    setNow(Date.now());
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, [active]);

  const elapsed = active && scheduledStart ? formatElapsedWith(scheduledStart, now) : "--:--";
  const total = scheduledStart && estimatedEnd ? formatDuration(scheduledStart, estimatedEnd) : "--:--";

  let cowsPerHour = 0;
  if (active && scheduledStart && cowCount && cowCount > 0) {
    const elapsedMinutes = (now - new Date(scheduledStart).getTime()) / 60000;
    if (elapsedMinutes > 0) {
      cowsPerHour = Math.round((cowCount / elapsedMinutes) * 60);
    }
  }

  return (
    <section className="card card-pad accent-panel">
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {active ? <span className="live-dot" /> : null}
        <span className={`status-tag ${active ? "status-success" : "status-neutral"}`}>{active ? "Active" : "Standby"}</span>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "end", gap: 16, marginTop: 16, flexWrap: "wrap" }}>
        <div>
          <div className="metric" style={{ fontSize: 34, color: "#F7F5EF" }}>
            {elapsed} / {total}
          </div>
          <div style={{ color: "#C9DAD0", marginTop: 8 }}>
            {sessionId && sessionId !== "standby" ? `Session ${sessionId.slice(0, 8)}` : "No active session"} · {operator ?? "Unassigned operator"}
          </div>
        </div>
        <div>
          <div className="label" style={{ color: "#9CB3A4" }}>
            Throughput
          </div>
          <div style={{ fontFamily: "'Schibsted Grotesk', sans-serif", fontSize: 28, fontWeight: 800, color: "#F7F5EF" }}>
            {cowsPerHour > 0 ? `${cowsPerHour} cows/hr` : "N/A"}
          </div>
        </div>
      </div>
    </section>
  );
}

function formatElapsedWith(startTime: string, nowMs: number): string {
  const elapsed = Math.floor((nowMs - new Date(startTime).getTime()) / 1000);
  if (elapsed < 0) return "--:--";
  const m = Math.floor(elapsed / 60);
  const s = elapsed % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}
