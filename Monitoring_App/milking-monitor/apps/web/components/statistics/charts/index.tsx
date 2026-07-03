export default function StatisticsCharts({ complianceScore }: { complianceScore?: number }) {
  const width = complianceScore ?? 0;
  return (
    <div className="card card-pad">
      <h2 className="section-title">Compliance Charts</h2>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${width}%` }} />
      </div>
      <div className="muted" style={{ fontSize: 13, marginTop: 8 }}>
        {width > 0 ? `${width}% overall compliance` : "No data available"}
      </div>
    </div>
  );
}
