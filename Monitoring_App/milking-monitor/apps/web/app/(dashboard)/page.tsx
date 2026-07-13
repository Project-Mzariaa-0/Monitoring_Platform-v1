import Link from "next/link";
import Go2rtcPlayer from "../../components/dashboard/go2rtc-player";
import { getMonitoringOverview } from "../../lib/data/store";
import { TASK_LABELS, TASK_ORDER, complianceScore } from "../../lib/constants";

export default async function DashboardPage() {
  const overview = await getMonitoringOverview();
  const session = overview.activeSession;
  const score = complianceScore(overview.missedCount);

  const metrics = [
    { label: "Sessions today", value: overview.totalSessions },
    { label: "Active alerts", value: overview.missedCount },
    { label: "Missed tasks", value: overview.missedCount },
  ];

  const missedTasks = overview.activeTaskEvents.filter(
    (t) => t.status === "missed" || t.override_status === "missed",
  );

  return (
    <div className="page-grid">
      <section className="card card-pad accent-panel">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 24, flexWrap: "wrap" }}>
          <div>
            <span className="status-tag status-success">
              <span className="live-dot" />
              {session?.status === "active" ? "Active" : "Standby"}
            </span>
            <h2 style={{ margin: "18px 0 8px", fontFamily: "'Schibsted Grotesk', sans-serif", fontSize: 34 }}>
              {session ? `Session ${session.id.slice(0, 8)}` : "No active session"}
            </h2>
            <p style={{ maxWidth: 680, color: "#C9DAD0", margin: 0 }}>
              {session
                ? `${session.employee_name} is assigned to two monitored positions with live compliance capture.`
                : "Schedule a session to activate the two-position monitoring grid and realtime alert stream."}
            </p>
          </div>
          <div style={{ minWidth: 220 }}>
            <div className="label" style={{ color: "#9CB3A4" }}>
              Compliance score
            </div>
            <div className="metric" style={{ color: "#F7F5EF" }}>
              {score}%
            </div>
            <div className="progress-track" style={{ marginTop: 12, background: "rgba(255,255,255,.18)" }}>
              <div className="progress-fill" style={{ width: `${score}%`, background: "#F7F5EF" }} />
            </div>
          </div>
        </div>
      </section>

      <section className="grid-3">
        {metrics.map((metric) => (
          <article key={metric.label} className="card card-pad">
            <span className="label">{metric.label}</span>
            <div className="metric">{metric.value}</div>
          </article>
        ))}
      </section>

      <section className="dashboard-grid">
        <div className="grid-2">
          {[1, 2].map((position) => {
            const positionTasks = overview.activeTaskEvents.filter((t) => {
              const cp = overview.activeCowProcesses.find((c) => c.id === t.cow_process_id && c.cow_position === position);
              return Boolean(cp);
            });
            const hasViolation = positionTasks.some((t) => t.status === "missed" || t.override_status === "missed");

            return (
              <article key={position} className="card card-pad">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <div>
                    <span className="label">Cow position {position}</span>
                    <strong>Process compliance</strong>
                  </div>
                  <span className={`status-tag ${hasViolation ? "status-danger" : "status-success"}`}>
                    {hasViolation ? "Violation" : session ? "Milking" : "Standby"}
                  </span>
                </div>
                <Go2rtcPlayer
                  src={`camera${position}`}
                  fallbackSrc={`fallback${position}`}
                  style={{ height: 180, borderRadius: 10 }}
                />
                <div style={{ marginTop: 14 }}>
                  {TASK_ORDER.slice(0, 4).map((taskId) => {
                    const event = positionTasks.find((t) => t.task_id === taskId);
                    const status = event?.override_status ?? event?.status ?? "pending";
                    const checked = status === "completed";
                    return (
                      <div className="check-row" key={taskId}>
                        <span>{TASK_LABELS[taskId]}</span>
                        <span className={`status-tag ${checked ? "status-success" : "status-neutral"}`}>
                          {checked ? "Checked" : "Pending"}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </article>
            );
          })}
        </div>

        <aside className="card card-pad">
          <h2 className="section-title">Recent Alerts Log</h2>
          <div className="rail-list">
            {missedTasks.length === 0 ? (
              <div className="alert-item" style={{ borderLeftColor: "var(--accent)" }}>
                <strong>No open alerts</strong>
                <p className="muted" style={{ margin: "6px 0 0" }}>
                  The current unit has no unresolved compliance exceptions.
                </p>
              </div>
            ) : (
              missedTasks.slice(0, 4).map((task) => {
                const cp = overview.activeCowProcesses.find((c) => c.id === task.cow_process_id);
                return (
                  <div className="alert-item" key={task.id}>
                    <strong>{TASK_LABELS[task.task_id] ?? task.task_id} missed</strong>
                    <p className="muted" style={{ margin: "6px 0 0" }}>
                      Position {cp?.cow_position ?? "unknown"} · review clip
                    </p>
                  </div>
                );
              })
            )}
          </div>
          <Link className="button button-primary" href="/live" style={{ width: "100%", marginTop: 16 }}>
            Open Live View
          </Link>
        </aside>
      </section>
    </div>
  );
}
