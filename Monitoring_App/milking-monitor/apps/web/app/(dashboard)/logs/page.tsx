import { listSessions, getSessionDetails } from "../../../lib/data/store";
import { TASK_LABELS } from "../../../lib/constants";

export default async function LogsPage() {
  const sessions = await listSessions();

  const enrichedSessions = await Promise.all(
    sessions.slice(0, 20).map(async (session) => {
      const details = await getSessionDetails(session.id);
      const missedTasks = details?.taskEvents.filter((t) => t.status === "missed" || t.override_status === "missed") ?? [];
      const cowPositions = details?.cowProcesses ?? [];
      return { ...session, missedTasks, cowPositions };
    }),
  );

  const logRows = enrichedSessions.flatMap((session) =>
    session.missedTasks.map((task) => ({
      id: task.id,
      severity: task.override_status === "missed" ? "warning" as const : "critical" as const,
      task_id: task.task_id,
      task_label: TASK_LABELS[task.task_id] ?? task.task_id,
      cow_position: session.cowPositions.find((c) => c.id === task.cow_process_id)?.cow_position ?? 0,
      timestamp: task.detected_start_time ?? session.updated_at,
      employee_name: session.employee_name,
      session_id: session.id,
    })),
  );

  return (
    <div className="page-grid">
      <section className="card card-pad">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
          <div>
            <h2 className="section-title">Audit History</h2>
            <p className="muted" style={{ margin: 0 }}>
              Severity, cow ID, task state, clip review, and override actions for the unit.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {["All", "Critical", "Warning"].map((filter) => (
              <span className="status-pill status-neutral" key={filter}>
                {filter}
              </span>
            ))}
          </div>
        </div>
      </section>
      <section className="card card-pad">
        <table className="table">
          <thead>
            <tr>
              <th>Severity</th>
              <th>Cow ID</th>
              <th>Task</th>
              <th>Timestamp</th>
              <th>Assigned employee</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {logRows.length === 0 ? (
              <tr>
                <td colSpan={6} className="muted">
                  No unit logs have been recorded yet.
                </td>
              </tr>
            ) : (
              logRows.map((row) => (
                <tr key={row.id}>
                  <td>
                    <span className={`status-pill ${row.severity === "critical" ? "status-danger" : "status-warning"}`}>
                      {row.severity === "critical" ? "Critical" : "Warning"}
                    </span>
                  </td>
                  <td>COW-{String(row.cow_position).padStart(3, "0")}</td>
                  <td>{row.task_label}</td>
                  <td>{new Date(row.timestamp).toLocaleString()}</td>
                  <td>{row.employee_name}</td>
                  <td>
                    <a className="button button-secondary" href={`/sessions/${row.session_id}`}>
                      Review
                    </a>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
