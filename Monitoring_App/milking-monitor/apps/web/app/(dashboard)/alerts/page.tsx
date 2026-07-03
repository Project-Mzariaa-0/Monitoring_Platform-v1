import { getMonitoringOverview } from "../../../lib/data/store";
import { TASK_LABELS } from "../../../lib/constants";

export default async function AlertsPage() {
  const overview = await getMonitoringOverview();

  const missedTasks = overview.activeTaskEvents.filter(
    (t) => t.status === "missed" || t.override_status === "missed",
  );

  return (
    <div className="page-grid">
      <section className="card card-pad">
        <h1 className="section-title" style={{ fontSize: 22 }}>
          Alerts
        </h1>
        <p className="muted">Review active and historical compliance alerts.</p>
      </section>
      {missedTasks.length === 0 ? (
        <article className="card card-pad" style={{ borderLeft: "4px solid var(--accent)" }}>
          <div className="muted" style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase" }}>
            Info
          </div>
          <div style={{ fontWeight: 700, marginTop: 8 }}>No active alerts</div>
          <div className="muted" style={{ fontSize: 14, marginTop: 4 }}>
            All compliance events are within normal parameters.
          </div>
        </article>
      ) : (
        missedTasks.map((task) => {
          const cowProcess = overview.activeCowProcesses.find((c) => c.id === task.cow_process_id);
          const isOverride = Boolean(task.override_status);
          const level = isOverride ? "warning" : "critical";
          return (
            <article
              key={task.id}
              className="card card-pad"
              style={{ borderLeft: `4px solid ${level === "critical" ? "var(--danger)" : "var(--warning)"}` }}
            >
              <div className="muted" style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase" }}>
                {level}
              </div>
              <div style={{ fontWeight: 700, marginTop: 8 }}>
                {TASK_LABELS[task.task_id] ?? task.task_id} missed
              </div>
              <div className="muted" style={{ fontSize: 14, marginTop: 4 }}>
                Position {cowProcess?.cow_position ?? "unknown"} ·{" "}
                {task.detected_start_time
                  ? new Date(task.detected_start_time).toLocaleTimeString()
                  : "Unknown time"}
              </div>
            </article>
          );
        })
      )}
    </div>
  );
}
