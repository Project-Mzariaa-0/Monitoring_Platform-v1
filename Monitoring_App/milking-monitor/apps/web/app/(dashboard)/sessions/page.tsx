import Link from "next/link";
import { listSessions, getEmployeeAnalytics } from "../../../lib/data/store";

export default async function SessionsPage() {
  const [sessions, employeeAnalytics] = await Promise.all([
    listSessions(),
    getEmployeeAnalytics(),
  ]);

  const employeeMap = new Map(employeeAnalytics.map((e) => [e.employee_name, e]));

  return (
    <div className="page-grid">
      <section className="card card-pad">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h1 className="section-title" style={{ fontSize: 22, margin: 0 }}>
              Session History
            </h1>
            <p className="muted" style={{ margin: "4px 0 0" }}>
              {sessions.length} total sessions
            </p>
          </div>
          <Link className="button button-primary" href="/scheduler/new">
            + New Session
          </Link>
        </div>
      </section>

      <section className="card card-pad">
        <table className="table">
          <thead>
            <tr>
              <th>Session</th>
              <th>Employee</th>
              <th>Scheduled</th>
              <th>Status</th>
              <th>Compliance</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {sessions.length === 0 ? (
              <tr>
                <td colSpan={6} className="muted" style={{ textAlign: "center", padding: 32 }}>
                  No sessions found. Create one to get started.
                </td>
              </tr>
            ) : (
              sessions.map((s) => {
                const emp = employeeMap.get(s.employee_name);
                const compliance = emp?.compliance ?? null;
                return (
                  <tr key={s.id}>
                    <td>
                      <Link href={`/sessions/${s.id}`} style={{ fontWeight: 600, color: "var(--accent)" }}>
                        {s.id.slice(0, 8)}
                      </Link>
                      <div className="muted" style={{ fontSize: 12 }}>
                        {s.supervisor_name}
                      </div>
                    </td>
                    <td>{s.employee_name}</td>
                    <td>
                      <div style={{ fontSize: 13 }}>
                        {new Date(s.scheduled_start_time).toLocaleDateString()}
                      </div>
                      <div className="muted" style={{ fontSize: 12 }}>
                        {new Date(s.scheduled_start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </div>
                    </td>
                    <td>
                      <span
                        className={`status-tag ${
                          s.status === "completed"
                            ? "status-success"
                            : s.status === "active"
                            ? "status-warning"
                            : s.status === "ended_early"
                            ? "status-danger"
                            : ""
                        }`}
                      >
                        {s.status.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td>
                      {compliance !== null ? (
                        <span
                          style={{
                            fontWeight: 700,
                            color: compliance >= 90 ? "var(--success)" : compliance >= 75 ? "var(--warning)" : "var(--danger)",
                          }}
                        >
                          {compliance}%
                        </span>
                      ) : (
                        <span className="muted">N/A</span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: 8 }}>
                        <Link className="button button-secondary" href={`/sessions/${s.id}`} style={{ fontSize: 12, padding: "4px 12px" }}>
                          Detail
                        </Link>
                        {s.status === "active" && (
                          <Link className="button button-primary" href={`/sessions/${s.id}/live`} style={{ fontSize: 12, padding: "4px 12px" }}>
                            Live
                          </Link>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
