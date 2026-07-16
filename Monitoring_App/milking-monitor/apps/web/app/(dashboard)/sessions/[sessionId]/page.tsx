import Link from "next/link";
import { getSessionDetails } from "../../../../lib/data/store";
import { TASK_LABELS } from "../../../../lib/constants";
import SessionActions from "../../../../components/dashboard/session-actions";
import ReportGenerator from "../../../../components/reports/report-generator";

export default async function SessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  const details = await getSessionDetails(sessionId);

  if (!details) {
    return (
      <div className="page-grid">
        <section className="card card-pad">
          <h1 className="section-title">Session not found</h1>
          <Link className="button button-secondary" href="/sessions">
            Back to sessions
          </Link>
        </section>
      </div>
    );
  }

  const { session, cowProcesses, taskEvents } = details;

  // Compute per-task analytics for this session
  const taskStats = new Map<string, { completed: number; missed: number; total: number; totalDuration: number }>();
  for (const te of taskEvents) {
    const existing = taskStats.get(te.task_id) ?? { completed: 0, missed: 0, total: 0, totalDuration: 0 };
    existing.total += 1;
    if (te.status === "completed") existing.completed += 1;
    if (te.status === "missed" || te.override_status === "missed") existing.missed += 1;
    existing.totalDuration += te.duration_seconds;
    taskStats.set(te.task_id, existing);
  }

  const completedTasks = taskEvents.filter((t) => t.status === "completed").length;
  const missedTasks = taskEvents.filter((t) => t.status === "missed" || t.override_status === "missed").length;
  const compliance = taskEvents.length > 0 ? Math.round((completedTasks / taskEvents.length) * 100) : 0;
  const avgDuration = taskEvents.length > 0 ? Math.round(taskEvents.reduce((sum, t) => sum + t.duration_seconds, 0) / taskEvents.length) : 0;

  return (
    <div className="page-grid">
      {/* Header */}
      <section className="card card-pad">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
          <div>
            <div className="muted" style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase" }}>
              Session detail
            </div>
            <h1 className="section-title" style={{ fontSize: 22, margin: "4px 0" }}>
              Session {sessionId.slice(0, 8)}
            </h1>
            <p className="muted" style={{ margin: 0 }}>
              {session.employee_name} · {session.supervisor_name}
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Link className="button button-primary" href={`/sessions/${sessionId}/live`}>
              Open live view
            </Link>
            <ReportGenerator sessionId={sessionId} />
          </div>
        </div>
        <SessionActions
          sessionId={sessionId}
          employeeName={session.employee_name}
          supervisorName={session.supervisor_name}
          supervisorEmail={session.supervisor_email}
        />
      </section>

      {/* Session Info + Compliance */}
      <section className="grid-2">
        <article className="card card-pad">
          <h2 className="section-title">Session Info</h2>
          <div className="data-row">
            <span>Status</span>
            <span className={`status-tag ${session.status === "completed" ? "status-success" : session.status === "active" ? "status-warning" : ""}`}>
              {session.status.replace(/_/g, " ")}
            </span>
          </div>
          <div className="data-row">
            <span>Scheduled Start</span>
            <strong>{new Date(session.scheduled_start_time).toLocaleString()}</strong>
          </div>
          <div className="data-row">
            <span>Estimated End</span>
            <strong>{new Date(session.estimated_end_time).toLocaleString()}</strong>
          </div>
          {session.actual_end_time && (
            <div className="data-row">
              <span>Actual End</span>
              <strong>{new Date(session.actual_end_time).toLocaleString()}</strong>
            </div>
          )}
          <div className="data-row">
            <span>Row 1 Cows</span>
            <strong>{session.row_1_cow_count}</strong>
          </div>
          <div className="data-row">
            <span>Row 2 Cows</span>
            <strong>{session.row_2_cow_count}</strong>
          </div>
        </article>

        <article className="card card-pad">
          <h2 className="section-title">Session Performance</h2>
          <div style={{ display: "flex", gap: 24, alignItems: "center", flexWrap: "wrap" }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8, minWidth: 120 }}>
              <div className="metric" style={{ fontSize: 36 }}>
                {compliance}%
              </div>
              <span className={`status-tag ${compliance >= 90 ? "status-success" : compliance >= 75 ? "status-warning" : "status-danger"}`}>
                {compliance >= 90 ? "Compliant" : compliance >= 75 ? "Review" : "Non-Compliant"}
              </span>
            </div>
            <div style={{ flex: 1 }}>
              <div className="data-row">
                <span>Total Tasks</span>
                <strong>{taskEvents.length}</strong>
              </div>
              <div className="data-row">
                <span>Completed</span>
                <strong style={{ color: "var(--success)" }}>{completedTasks}</strong>
              </div>
              <div className="data-row">
                <span>Missed</span>
                <strong style={{ color: missedTasks > 0 ? "var(--danger)" : undefined }}>{missedTasks}</strong>
              </div>
              <div className="data-row">
                <span>Avg Duration</span>
                <strong>{avgDuration}s</strong>
              </div>
              <div className="data-row">
                <span>Cow Processes</span>
                <strong>{cowProcesses.length}</strong>
              </div>
            </div>
          </div>
        </article>
      </section>

      {/* Task Breakdown */}
      <section className="card card-pad">
        <h2 className="section-title">Task Breakdown</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Task</th>
              <th>Completed</th>
              <th>Missed</th>
              <th>Avg Duration</th>
              <th>Compliance</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(TASK_LABELS).map(([taskId, label]) => {
              const stats = taskStats.get(taskId);
              if (!stats) {
                return (
                  <tr key={taskId}>
                    <td>{label}</td>
                    <td className="muted">0</td>
                    <td className="muted">0</td>
                    <td className="muted">N/A</td>
                    <td className="muted">N/A</td>
                  </tr>
                );
              }
              const taskCompliance = stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0;
              const avgTaskDuration = stats.total > 0 ? Math.round(stats.totalDuration / stats.total) : 0;
              return (
                <tr key={taskId}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{label}</div>
                    <div className="muted" style={{ fontSize: 12 }}>{taskId}</div>
                  </td>
                  <td style={{ color: "var(--success)" }}>{stats.completed}</td>
                  <td style={{ color: stats.missed > 0 ? "var(--danger)" : undefined }}>{stats.missed}</td>
                  <td>{avgTaskDuration}s</td>
                  <td>
                    <span
                      style={{
                        fontWeight: 700,
                        color: taskCompliance >= 90 ? "var(--success)" : taskCompliance >= 75 ? "var(--warning)" : "var(--danger)",
                      }}
                    >
                      {taskCompliance}%
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      {/* Cow Processes */}
      {cowProcesses.length > 0 && (
        <section className="card card-pad">
          <h2 className="section-title">Cow Processes</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Position</th>
                <th>Start Time</th>
                <th>End Time</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {cowProcesses.map((cp) => (
                <tr key={cp.id}>
                  <td>Row {cp.cow_position}</td>
                  <td>{cp.detected_start_time ? new Date(cp.detected_start_time).toLocaleString() : "N/A"}</td>
                  <td>{cp.detected_end_time ? new Date(cp.detected_end_time).toLocaleString() : "N/A"}</td>
                  <td>
                    <span className={`status-tag ${cp.overall_status === "completed" ? "status-success" : cp.overall_status === "in_progress" ? "status-warning" : ""}`}>
                      {cp.overall_status.replace(/_/g, " ")}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {/* Task Events */}
      {taskEvents.length > 0 && (
        <section className="card card-pad">
          <h2 className="section-title">Task Events</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Task</th>
                <th>Start Time</th>
                <th>End Time</th>
                <th>Duration</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {taskEvents.map((te) => (
                <tr key={te.id}>
                  <td>{te.task_id}</td>
                  <td>{te.detected_start_time ? new Date(te.detected_start_time).toLocaleString() : "N/A"}</td>
                  <td>{te.detected_end_time ? new Date(te.detected_end_time).toLocaleString() : "N/A"}</td>
                  <td>{te.duration_seconds}s</td>
                  <td>
                    <span className={`status-tag ${te.override_status === "completed" || te.status === "completed" ? "status-success" : te.status === "missed" ? "status-danger" : ""}`}>
                      {(te.override_status ?? te.status).replace(/_/g, " ")}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
