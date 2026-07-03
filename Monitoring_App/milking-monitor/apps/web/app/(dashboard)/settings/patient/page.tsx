import { getMonitoringOverview } from "../../../../lib/data/store";

export default async function PatientSettingsPage() {
  const overview = await getMonitoringOverview();

  const cowProcesses = overview.activeCowProcesses.length > 0
    ? overview.activeCowProcesses
    : [];

  return (
    <section className="card card-pad">
      <h2 className="section-title">Registered Herd Metadata</h2>
      {cowProcesses.length === 0 ? (
        <p className="muted">No cow processes recorded yet. Start a session to track herd data.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Cow Process ID</th>
              <th>Session</th>
              <th>Position</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {cowProcesses.map((cp) => (
              <tr key={cp.id}>
                <td>{cp.id.slice(0, 8)}</td>
                <td>{cp.session_id.slice(0, 8)}</td>
                <td>Position {cp.cow_position}</td>
                <td>
                  <span className={`status-tag ${cp.overall_status === "completed" ? "status-success" : cp.overall_status === "in_progress" ? "status-warning" : "status-neutral"}`}>
                    {cp.overall_status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
