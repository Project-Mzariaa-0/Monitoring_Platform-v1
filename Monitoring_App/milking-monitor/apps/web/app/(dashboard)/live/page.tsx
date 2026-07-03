import Link from "next/link";
import LiveSessionBanner from "../../../components/dashboard/live-session-banner";
import LiveSessionStream from "../../../components/dashboard/live-session-stream";
import TaskChecklist from "../../../components/dashboard/task-checklist";
import { getMonitoringOverview } from "../../../lib/data/store";
import { TASK_LABELS, TASK_ORDER, complianceScore } from "../../../lib/constants";

export default async function LivePage() {
  const overview = await getMonitoringOverview();
  const sessionId = overview.activeSession?.id ?? "standby";

  const initialEvents = overview.activeTaskEvents.map((taskEvent) => ({
    session_id: sessionId,
    type: taskEvent.status,
    payload: {
      task_id: taskEvent.task_id,
      cow_process_id: taskEvent.cow_process_id,
      status: taskEvent.status,
      duration_seconds: taskEvent.duration_seconds,
    },
  }));

  const missedTasks = overview.activeTaskEvents.filter(
    (t) => t.status === "missed" || t.override_status === "missed",
  );

  return (
    <div className="dashboard-grid">
      <div className="page-grid">
        <LiveSessionBanner
          sessionId={overview.activeSession?.id}
          operator={overview.activeSession?.employee_name}
          active={overview.activeSession?.status === "active"}
          scheduledStart={overview.activeSession?.scheduled_start_time}
          estimatedEnd={overview.activeSession?.estimated_end_time}
          cowCount={(overview.activeSession?.row_1_cow_count ?? 0) + (overview.activeSession?.row_2_cow_count ?? 0)}
        />
        <div className="grid-2">
          {[1, 2].map((position) => {
            const positionTasks = overview.activeTaskEvents.filter(
              (t) => overview.activeCowProcesses.find((c) => c.id === t.cow_process_id && c.cow_position === position),
            );
            const hasViolation = positionTasks.some((t) => t.status === "missed" || t.override_status === "missed");

            return (
              <article key={position} className="card card-pad">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <div>
                    <span className="label">Position {position}</span>
                    <strong>Camera feed</strong>
                  </div>
                  <span className={`status-tag ${hasViolation ? "status-danger" : "status-success"}`}>
                    {hasViolation ? "Violation" : overview.activeSession ? "Milking" : "Standby"}
                  </span>
                </div>
                <div className="video-frame">
                  <div className="roi-box" />
                </div>
                <div style={{ marginTop: 14 }}>
                  {TASK_ORDER.map((taskId) => {
                    const event = positionTasks.find((t) => t.task_id === taskId);
                    const status = event?.override_status ?? event?.status ?? "pending";
                    const statusLabel =
                      status === "completed"
                        ? "Checked"
                        : status === "missed" || status === "anomaly_flagged"
                          ? "Missed"
                          : status === "unverifiable"
                            ? "Unverifiable"
                            : "Pending";
                    const pillClass =
                      status === "completed"
                        ? "status-success"
                        : status === "missed" || status === "anomaly_flagged"
                          ? "status-danger"
                          : status === "unverifiable"
                            ? "status-warning"
                            : "status-neutral";

                    return (
                      <div className="check-row" key={taskId}>
                        <span>
                          <strong>{taskId}</strong> · {TASK_LABELS[taskId]}
                        </span>
                        <span className={`status-tag ${pillClass}`}>{statusLabel}</span>
                      </div>
                    );
                  })}
                </div>
                {hasViolation ? (
                  <div className="muted" style={{ marginTop: 14, fontSize: 13 }}>
                    Violation flagged — review in audit log
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
        {overview.activeSession ? (
          <>
            <LiveSessionStream sessionId={overview.activeSession.id} initialEvents={initialEvents} />
            <TaskChecklist sessionId={overview.activeSession.id} taskEvents={overview.activeTaskEvents} />
          </>
        ) : (
          <section className="card card-pad">
            <h2 className="section-title">Realtime feed</h2>
            <p className="muted">No active session is available. Start or schedule a session before opening the stream.</p>
            <Link className="button button-primary" href="/scheduler/new">
              New Session
            </Link>
          </section>
        )}
      </div>

      <aside className="card card-pad" style={{ alignSelf: "start", position: "sticky", top: 96 }}>
        <h2 className="section-title">Recent Alerts Log</h2>
        <div className="rail-list">
          {missedTasks.length === 0 ? (
            <div className="alert-item" style={{ borderLeftColor: "var(--accent)" }}>
              <strong>No active exceptions</strong>
              <p className="muted" style={{ margin: "6px 0 0" }}>
                Compliance events will appear here as the inference service publishes them.
              </p>
            </div>
          ) : (
            missedTasks.slice(0, 6).map((task) => (
              <div className="alert-item" key={task.id}>
                <strong>{TASK_LABELS[task.task_id] ?? task.task_id} requires review</strong>
                <p className="muted" style={{ margin: "6px 0 8px" }}>
                  {task.detected_start_time ? new Date(task.detected_start_time).toLocaleTimeString() : "Unknown time"} ·{" "}
                  {(() => {
                    const cp = overview.activeCowProcesses.find((c) => c.id === task.cow_process_id);
                    return cp ? `Position ${cp.cow_position}` : "Unknown position";
                  })()}
                </p>
                <div style={{ display: "flex", gap: 10 }}>
                  <Link className="small-muted" href={`/sessions/${sessionId}`}>
                    View clip
                  </Link>
                  <span className="small-muted">Dismiss</span>
                </div>
              </div>
            ))
          )}
        </div>
        <div style={{ marginTop: 18 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <strong>Compliance score</strong>
            <strong>{complianceScore(overview.missedCount)}%</strong>
          </div>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${complianceScore(overview.missedCount)}%` }} />
          </div>
        </div>
      </aside>
    </div>
  );
}
