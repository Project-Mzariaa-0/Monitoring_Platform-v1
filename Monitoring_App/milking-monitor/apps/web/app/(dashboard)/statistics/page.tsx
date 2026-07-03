import { getStatistics } from "../../../lib/data/store";

export default async function StatisticsPage() {
  const statistics = await getStatistics();

  return (
    <div className="page-grid">
      <section className="card card-pad">
        <h1 className="section-title" style={{ fontSize: 22 }}>
          Statistics
        </h1>
        <p className="muted">Historical compliance metrics, missed tasks, and duration trends.</p>
      </section>
      <section className="card card-pad">
        <div className="metric">{Math.max(0, 100 - statistics.missedCount)}%</div>
        <div className="muted">Average completion rate across {statistics.totalSessions} sessions</div>
      </section>
      <section className="card card-pad">
        <div style={{ fontWeight: 700 }}>Completed sessions: {statistics.completedSessions}</div>
        <div className="muted" style={{ marginTop: 8 }}>
          Missed tasks: {statistics.missedCount} · Average task duration: {statistics.averageDuration}s
        </div>
      </section>
    </div>
  );
}
