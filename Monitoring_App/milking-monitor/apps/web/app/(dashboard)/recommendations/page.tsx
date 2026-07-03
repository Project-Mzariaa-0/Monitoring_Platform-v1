import { getMonitoringOverview, getStatistics } from "../../../lib/data/store";
import { complianceScore } from "../../../lib/constants";

export default async function RecommendationsPage() {
  const [overview, statistics] = await Promise.all([getMonitoringOverview(), getStatistics()]);
  const score = complianceScore(statistics.missedCount);

  let riskLevel = "Low";
  let riskColor = "var(--success)";
  let recommendation = "All compliance parameters are within normal range. Continue standard monitoring.";

  if (score < 75) {
    riskLevel = "Critique";
    riskColor = "var(--danger)";
    recommendation = "Multiple tasks are being missed. Review operator protocols and increase supervision frequency immediately.";
  } else if (score < 90) {
    riskLevel = "Elevated";
    riskColor = "var(--warning)";
    recommendation = "Some compliance drift detected. Review task timing thresholds and verify equipment calibration.";
  }

  return (
    <div className="page-grid">
      <section className="card card-pad" style={{ background: "linear-gradient(135deg, rgba(0,63,123,0.12), rgba(186,26,26,0.08)), #fff" }}>
        <h1 className="section-title" style={{ fontSize: 22 }}>
          Recommendations
        </h1>
        <p className="muted">Positioning guidance and care actions based on the current risk level.</p>
      </section>
      <section className="card card-pad">
        <div className="metric" style={{ fontSize: 28, color: riskColor }}>
          {riskLevel}
        </div>
        <div className="muted">{recommendation}</div>
        <div style={{ marginTop: 16 }}>
          <div className="data-row">
            <span>Compliance score</span>
            <strong>{score}%</strong>
          </div>
          <div className="data-row">
            <span>Total missed tasks</span>
            <strong>{statistics.missedCount}</strong>
          </div>
          <div className="data-row">
            <span>Active sessions</span>
            <strong>{overview.activeCount}</strong>
          </div>
        </div>
      </section>
    </div>
  );
}
