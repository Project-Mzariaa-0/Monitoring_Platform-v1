import Link from "next/link";
import { listSessions } from "../../../lib/data/store";

export default async function SchedulerPage() {
  const sessions = await listSessions();

  return (
    <div className="page-grid">
      <section className="card card-pad">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <div>
            <h2 className="section-title">Upcoming and Past Sessions</h2>
            <p className="muted" style={{ margin: 0 }}>
              Assign operators, review windows, and open active session details.
            </p>
          </div>
          <Link className="button button-primary" href="/scheduler/new">
            New Session
          </Link>
        </div>
      </section>
      <section className="card card-pad">
        <table className="table">
          <thead>
            <tr>
              <th>Session</th>
              <th>Timing</th>
              <th>Operator</th>
              <th>Herd</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {sessions.length === 0 ? (
              <tr>
                <td colSpan={6} className="muted">
                  No sessions scheduled yet.
                </td>
              </tr>
            ) : (
              sessions.map((session) => (
                <tr key={session.id}>
                  <td>{session.id}</td>
                  <td>{new Date(session.scheduled_start_time).toLocaleString()}</td>
                  <td>{session.employee_name}</td>
                  <td>{session.row_1_cow_count + session.row_2_cow_count} cows</td>
                  <td>
                    <span className={`status-tag ${session.status === "active" ? "status-success" : "status-neutral"}`}>{session.status}</span>
                  </td>
                  <td>
                    <Link className="button button-secondary" href={`/sessions/${session.id}`}>
                      Open
                    </Link>
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
