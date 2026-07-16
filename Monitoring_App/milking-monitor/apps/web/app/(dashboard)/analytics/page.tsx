import Link from "next/link";
import ReportGenerator from "../../../components/reports/report-generator";
import { getMonitoringOverview, getStatistics, getEmployeeAnalytics, getTaskAnalytics } from "../../../lib/data/store";
import { complianceScore, complianceLabel } from "../../../lib/constants";

export default async function AnalyticsPage() {
  const [statistics, overview, employeeAnalytics, taskAnalytics] = await Promise.all([
    getStatistics(),
    getMonitoringOverview(),
    getEmployeeAnalytics(),
    getTaskAnalytics(),
  ]);

  const score = complianceScore(statistics.missedCount);
  const status = complianceLabel(score);
  const sessionId = overview.activeSession?.id ?? null;

  return (
    <div className="page-grid">
      <section className="card card-pad">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
          <div>
            <span className="label">Reporting period</span>
            <strong>Current operational window · All positions</strong>
          </div>
          {sessionId ? (
            <ReportGenerator sessionId={sessionId} />
          ) : (
            <span className="muted">No active session to report</span>
          )}
        </div>
      </section>

      <section className="grid-2">
        <article className="card card-pad">
          <h2 className="section-title">System Compliance Score</h2>
          <div style={{ display: "flex", gap: 24, alignItems: "center", flexWrap: "wrap" }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, minWidth: 140 }}>
              <div className="metric" style={{ fontSize: 36 }}>
                {score}%
              </div>
              <span className={`status-tag ${score >= 90 ? "status-success" : score >= 75 ? "status-warning" : "status-danger"}`}>
                {status}
              </span>
            </div>
            <div>
              <div className="data-row">
                <span>Completed sessions</span>
                <strong>{statistics.completedSessions}</strong>
              </div>
              <div className="data-row">
                <span>Missed tasks</span>
                <strong>{statistics.missedCount}</strong>
              </div>
              <div className="data-row">
                <span>Average task duration</span>
                <strong>{statistics.averageDuration}s</strong>
              </div>
            </div>
          </div>
        </article>

        <article className="card card-pad">
          <h2 className="section-title">Missed Task Frequency</h2>
          <div className="rail-list">
            {taskAnalytics.map((task) => {
              const missedRate = task.total > 0 ? Math.round((task.missed / task.total) * 100) : 0;
              const completedRate = 100 - missedRate;
              return (
                <div key={task.task_id}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <span>{task.label}</span>
                    <span className="small-muted">{missedRate}% missed</span>
                  </div>
                  <div className="progress-track">
                    <div className="progress-fill" style={{ width: `${completedRate}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </article>
      </section>

      <section className="grid-2">
        <article className="card card-pad">
          <h2 className="section-title">Operational Efficiency</h2>
          {taskAnalytics.slice(0, 4).map((task) => (
            <div key={task.task_id} style={{ marginBottom: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span>{task.label}</span>
                <strong>{task.avg_duration_seconds > 0 ? `${task.avg_duration_seconds}s` : "N/A"}</strong>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${task.total > 0 ? Math.round((task.completed / task.total) * 100) : 0}%` }} />
              </div>
            </div>
          ))}
        </article>

        <article className="card card-pad">
          <h2 className="section-title">Human Factors</h2>
          {employeeAnalytics.length === 0 ? (
            <p className="muted">No employee data yet. Complete a session to see analytics.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Compliance</th>
                  <th>Avg speed</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {employeeAnalytics.map((emp) => (
                  <tr key={emp.employee_name}>
                    <td>{emp.employee_name}</td>
                    <td>{emp.compliance}%</td>
                    <td>{emp.avg_duration_seconds > 0 ? `${Math.floor(emp.avg_duration_seconds / 60)}m ${emp.avg_duration_seconds % 60}s` : "N/A"}</td>
                    <td>
                      <span className={`status-tag ${emp.status === "Review Req." ? "status-warning" : "status-success"}`}>{emp.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </article>
      </section>

      <section className="card card-pad accent-panel">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 20, flexWrap: "wrap" }}>
          <div>
            <h2 className="section-title" style={{ color: "#F7F5EF" }}>
              Predictive Compliance Logic
            </h2>
            <p style={{ color: "#C9DAD0", margin: 0, maxWidth: 680 }}>
              Post-dip drift is trending above threshold on faster cycles. Review protocol timing before the next peak window.
            </p>
          </div>
          <Link className="button button-secondary" href="/logs">
            Review Protocol Changes
          </Link>
        </div>
      </section>
    </div>
  );
}
