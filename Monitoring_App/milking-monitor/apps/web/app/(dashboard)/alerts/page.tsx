import { getOperationalAlerts } from "../../../lib/data/store";

export default async function AlertsPage() {
  const alerts = await getOperationalAlerts();

  return (
    <div className="page-grid">
      <section className="card card-pad">
        <h1 className="section-title" style={{ fontSize: 22 }}>
          Alerts
        </h1>
        <p className="muted">Review active and historical compliance alerts.</p>
      </section>
      {alerts.length === 0 ? (
        <article className="card card-pad" style={{ borderLeft: "4px solid var(--accent)" }}>
          <div className="muted" style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase" }}>
            Info
          </div>
          <div style={{ fontWeight: 700, marginTop: 8 }}>No active alerts</div>
          <div className="muted" style={{ fontSize: 14, marginTop: 4 }}>
            All compliance events are within normal parameters.
          </div>
        </article>
      ) : (
        alerts.map((alert) => {
          return (
            <article
              key={alert.id}
              className="card card-pad"
              style={{ borderLeft: `4px solid ${alert.level === "critical" ? "var(--danger)" : alert.level === "warning" ? "var(--warning)" : "var(--accent)"}` }}
            >
              <div className="muted" style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase" }}>
                {alert.level} · {alert.source}
              </div>
              <div style={{ fontWeight: 700, marginTop: 8 }}>
                {alert.title}
              </div>
              <div className="muted" style={{ fontSize: 14, marginTop: 4 }}>
                {alert.detail}
              </div>
            </article>
          );
        })
      )}
    </div>
  );
}
