import { getStatistics } from "../../../lib/data/store";
import ReportGenerator from "../../../components/reports/report-generator";

export default async function ReportsPage() {
  const statistics = await getStatistics();
  const latestSessionId = statistics.reports[0]?.session_id ?? null;

  return (
    <div className="page-grid">
      <section className="card card-pad">
        <h1 className="section-title" style={{ fontSize: 22 }}>
          Reports
        </h1>
        <p className="muted">Generate a Word report for a session or date range.</p>
        {latestSessionId ? (
          <ReportGenerator sessionId={latestSessionId} />
        ) : (
          <p className="muted">Complete a session first to generate reports.</p>
        )}
      </section>
      <section className="card card-pad">
        <h2 className="section-title">Recent reports</h2>
        <div className="page-grid">
          {statistics.reports.length === 0 ? (
            <p className="muted">No reports generated yet.</p>
          ) : (
            statistics.reports.map((report) => (
              <div key={report.id} className="nav-card" style={{ border: "1px solid var(--border)", borderRadius: 16 }}>
                <div>
                  <div style={{ fontWeight: 700 }}>{report.session_id.slice(0, 8)}</div>
                  <div className="muted" style={{ fontSize: 14 }}>
                    Generated {new Date(report.generated_at).toLocaleString()}
                  </div>
                </div>
                <a className="button button-secondary" href={report.docx_file_url}>
                  Download
                </a>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
