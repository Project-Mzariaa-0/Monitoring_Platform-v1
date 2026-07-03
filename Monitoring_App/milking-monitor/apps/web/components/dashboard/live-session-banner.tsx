function formatElapsed(startTime: string | null): string {
  if (!startTime) return "--:--";
  const elapsed = Math.floor((Date.now() - new Date(startTime).getTime()) / 1000);
  const m = Math.floor(elapsed / 60);
  const s = elapsed % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

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
  const elapsed = active && scheduledStart ? formatElapsed(scheduledStart) : "--:--";
  const total = scheduledStart && estimatedEnd ? formatDuration(scheduledStart, estimatedEnd) : "--:--";

  let cowsPerHour = 0;
  if (active && scheduledStart && cowCount && cowCount > 0) {
    const elapsedMinutes = (Date.now() - new Date(scheduledStart).getTime()) / 60000;
    if (elapsedMinutes > 0) {
      cowsPerHour = Math.round((cowCount / elapsedMinutes) * 60);
    }
  }

  return (
    <section className="card card-pad dark-panel">
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {active ? <span className="live-dot" /> : null}
        <span className={`status-pill ${active ? "status-success" : "status-neutral"}`}>{active ? "Active" : "Standby"}</span>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "end", gap: 16, marginTop: 16, flexWrap: "wrap" }}>
        <div>
          <div className="metric" style={{ fontSize: 34, color: "#fff" }}>
            {elapsed} / {total}
          </div>
          <div style={{ color: "#c7cdd9", marginTop: 8 }}>
            {sessionId && sessionId !== "standby" ? `Session ${sessionId.slice(0, 8)}` : "No active session"} · {operator ?? "Unassigned operator"}
          </div>
        </div>
        <div>
          <div className="label" style={{ color: "#9ca3af" }}>
            Throughput
          </div>
          <div style={{ fontFamily: "Manrope, Inter, sans-serif", fontSize: 28, fontWeight: 800, color: "var(--accent-bright)" }}>
            {cowsPerHour > 0 ? `${cowsPerHR(cowsPerHour)} cows/hr` : "N/A"}
          </div>
        </div>
      </div>
    </section>
  );
}

function cowsPerHR(value: number): string {
  return String(value);
}
