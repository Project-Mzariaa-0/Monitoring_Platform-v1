import Link from "next/link";
import { getSessionDetails } from "../../../../lib/data/store";
import SessionActions from "../../../../components/dashboard/session-actions";

export default async function SessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  const details = await getSessionDetails(sessionId);

  return (
    <div className="page-grid">
      <section className="card card-pad">
        <div className="muted" style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase" }}>
          Session detail
        </div>
        <h1 className="section-title" style={{ fontSize: 22 }}>
          Session {sessionId.slice(0, 8)}
        </h1>
        <p className="muted">
          {details?.session.employee_name ?? "Assigned employee"} · {details?.session.status ?? "unknown"}
        </p>
        <div style={{ display: "flex", gap: 12, marginTop: 16, flexWrap: "wrap" }}>
          <Link className="button button-primary" href={`/sessions/${sessionId}/live`}>
            Open live view
          </Link>
        </div>
        <SessionActions
          sessionId={sessionId}
          employeeName={details?.session.employee_name ?? "Assigned employee"}
          supervisorName={details?.session.supervisor_name ?? "Supervisor"}
          supervisorEmail={details?.session.supervisor_email ?? ""}
        />
      </section>
      <section className="card card-pad">
        <h2 className="section-title">Audit trail</h2>
        <div className="muted">{details?.cowProcesses.length ?? 0} cow processes tracked</div>
        <div className="muted" style={{ marginTop: 8 }}>
          {details?.taskEvents.length ?? 0} task events recorded
        </div>
      </section>
    </div>
  );
}
