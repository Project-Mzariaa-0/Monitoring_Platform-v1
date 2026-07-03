import { getMonitoringOverview } from "../../../lib/data/store";
import { TASK_LABELS, TASK_ORDER } from "../../../lib/constants";

export default async function MonitoringPage() {
  const overview = await getMonitoringOverview();
  const activeTasks = overview.activeTaskEvents;

  const position1Tasks = activeTasks.filter((t) => {
    const cp = overview.activeCowProcesses.find((c) => c.id === t.cow_process_id);
    return cp?.cow_position === 1;
  });
  const position2Tasks = activeTasks.filter((t) => {
    const cp = overview.activeCowProcesses.find((c) => c.id === t.cow_process_id);
    return cp?.cow_position === 2;
  });

  function taskColor(tasks: typeof activeTasks, taskId: string): string {
    const event = tasks.find((t) => t.task_id === taskId);
    if (!event) return "var(--neutral-soft)";
    const status = event.override_status ?? event.status;
    if (status === "completed") return "var(--success)";
    if (status === "missed" || status === "anomaly_flagged") return "var(--danger)";
    if (status === "unverifiable") return "var(--warning)";
    return "var(--neutral-soft)";
  }

  return (
    <div className="page-grid">
      <section className="card card-pad">
        <h1 className="section-title" style={{ fontSize: 22 }}>
          Monitoring
        </h1>
        <p className="muted">
          Full-resolution view of the two monitored cow positions and their task state.
          {overview.activeSession ? ` Active session ${overview.activeSession.id.slice(0, 8)}.` : " No active session found."}
        </p>
      </section>

      <section className="card card-pad">
        <div className="grid-2">
          {[1, 2].map((position) => {
            const tasks = position === 1 ? position1Tasks : position2Tasks;
            const cowProcess = overview.activeCowProcesses.find((c) => c.cow_position === position);
            return (
              <div key={position}>
                <div className="label">Cow position {position}</div>
                <div className="muted" style={{ fontSize: 13, marginBottom: 8 }}>
                  {cowProcess ? `Status: ${cowProcess.overall_status}` : "No active process"}
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
                  {TASK_ORDER.map((taskId) => (
                    <div
                      key={taskId}
                      title={TASK_LABELS[taskId]}
                      style={{
                        padding: "8px 4px",
                        borderRadius: 8,
                        background: taskColor(tasks, taskId),
                        color: "#fff",
                        fontSize: 11,
                        fontWeight: 600,
                        textAlign: "center",
                      }}
                    >
                      {taskId}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="card card-pad">
        <h2 className="section-title">System status</h2>
        <div className="nav-card" style={{ border: "1px solid var(--border)", borderRadius: 16 }}>
          <div>
            <div style={{ fontWeight: 700 }}>Inference service</div>
            <div className="muted" style={{ fontSize: 14 }}>
              {overview.activeCount > 0 ? `${overview.activeCount} active session(s) · ${overview.missedCount} missed tasks` : "Connected to RTSP stream and ingest API"}
            </div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              Current session: {overview.activeSession?.id.slice(0, 8) ?? "none"}
            </div>
          </div>
          <span style={{ width: 12, height: 12, borderRadius: 999, background: overview.activeCount > 0 ? "var(--success)" : "var(--neutral-soft)" }} />
        </div>
      </section>
    </div>
  );
}
