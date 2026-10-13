import EquipmentStatus from "../../../components/dashboard/equipment-status";
import { getModelHealthOverview, getMonitoringOverview } from "../../../lib/data/store";
import { formatUptime, getInferenceHealth } from "../../../lib/observability/health";

export default async function EquipmentPage() {
  const [modelHealth, inferenceHealth, monitoringOverview] = await Promise.all([
    getModelHealthOverview(),
    getInferenceHealth(),
    getMonitoringOverview(),
  ]);
  const services = [
    {
      name: "Inference Service",
      url: process.env.INFERENCE_SERVICE_URL || "http://localhost:8001",
      type: "api" as const,
    },
    {
      name: "RTSP Stream",
      url: process.env.RTSP_STREAM_URL || "Not configured",
      type: "stream" as const,
    },
    {
      name: "Event Ingestion",
      url: process.env.NEXTAUTH_URL || "http://localhost:3000",
      type: "api" as const,
    },
    {
      name: "YOLO Model",
      url: process.env.MODEL_WEIGHTS_PATH || "Not configured",
      type: "model" as const,
    },
  ];

  return (
    <div className="page-grid">
      <section className="card card-pad">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 16 }}>
          <div>
            <h2 className="section-title">Production Health</h2>
            <p className="muted" style={{ margin: 0 }}>Live service and session readiness.</p>
          </div>
          <span className={`status-tag ${inferenceHealth.status === "ok" ? "status-success" : inferenceHealth.status === "degraded" ? "status-warning" : "status-danger"}`}>
            {inferenceHealth.status === "ok" ? "Healthy" : inferenceHealth.status === "degraded" ? "Degraded" : "Offline"}
          </span>
        </div>
        <div className="grid-3" style={{ marginTop: 18 }}>
          <div><span className="label">Inference uptime</span><div className="metric" style={{ fontSize: 26 }}>{formatUptime(inferenceHealth.uptimeSeconds)}</div></div>
          <div><span className="label">Inference sessions</span><div className="metric">{inferenceHealth.activeSessions.length}</div></div>
          <div><span className="label">DB sessions today</span><div className="metric">{monitoringOverview.totalSessions}</div></div>
        </div>
        <div className="rail-list" style={{ marginTop: 18 }}>
          <div className="data-row"><div><strong>Inference readiness</strong><div className="muted" style={{ fontSize: 13 }}>{inferenceHealth.error ?? "Health endpoint responding"}</div></div><span className={`status-tag ${inferenceHealth.ready ? "status-success" : "status-danger"}`}>{inferenceHealth.ready ? "Ready" : "Not ready"}</span></div>
          <div className="data-row"><div><strong>Hybrid model</strong><div className="muted" style={{ fontSize: 13 }}>{inferenceHealth.hybridEnabled === null ? "Unavailable" : inferenceHealth.hybridEnabled ? "Enabled" : "Disabled"}</div></div><span className="status-tag status-neutral">Configured</span></div>
          <div className="data-row"><div><strong>Monitoring sessions</strong><div className="muted" style={{ fontSize: 13 }}>{monitoringOverview.activeCount} scheduled or active</div></div><span className="status-tag status-success">Tracked</span></div>
        </div>
      </section>
      <section className="card card-pad">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 16 }}>
          <div>
            <h2 className="section-title">Model Health</h2>
            <p className="muted" style={{ margin: 0 }}>Confidence and missed-task signals from persisted inference events.</p>
          </div>
          <span className={`status-tag ${modelHealth.averageConfidence >= 0.7 ? "status-success" : "status-warning"}`}>
            {modelHealth.totalEvents === 0 ? "No samples" : modelHealth.averageConfidence >= 0.7 ? "Stable" : "Review"}
          </span>
        </div>
        <div className="grid-3" style={{ marginTop: 18 }}>
          <div><span className="label">Events</span><div className="metric">{modelHealth.totalEvents}</div></div>
          <div><span className="label">Avg confidence</span><div className="metric">{Math.round(modelHealth.averageConfidence * 100)}%</div></div>
          <div><span className="label">Low confidence</span><div className="metric">{Math.round(modelHealth.lowConfidenceRate * 100)}%</div></div>
        </div>
        <div className="rail-list" style={{ marginTop: 18 }}>
          {modelHealth.tasks.length === 0 ? <div className="muted">No task events recorded yet.</div> : modelHealth.tasks.map((task) => (
            <div className="data-row" key={task.taskId}>
              <div><strong>{task.taskId}</strong><div className="muted" style={{ fontSize: 13 }}>{task.eventCount} events · {task.missedCount} missed</div></div>
              <span className={`status-tag ${task.averageConfidence >= 0.7 ? "status-success" : "status-warning"}`}>{Math.round(task.averageConfidence * 100)}%</span>
            </div>
          ))}
        </div>
      </section>
      <div className="grid-2">
      <section className="card card-pad">
        <h2 className="section-title">System Status</h2>
        <EquipmentStatus services={services} />
      </section>
      <section className="card card-pad">
        <h2 className="section-title">Configuration</h2>
        <div className="rail-list">
          <div className="data-row">
            <div>
              <strong>Database</strong>
              <div className="muted" style={{ fontSize: 13 }}>PostgreSQL 16</div>
            </div>
            <span className="status-tag status-success">Connected</span>
          </div>
          <div className="data-row">
            <div>
              <strong>Authentication</strong>
              <div className="muted" style={{ fontSize: 13 }}>NextAuth.js · JWT strategy</div>
            </div>
            <span className="status-tag status-success">Active</span>
          </div>
          <div className="data-row">
            <div>
              <strong>Email Service</strong>
              <div className="muted" style={{ fontSize: 13 }}>{process.env.RESEND_API_KEY ? "Resend configured" : "Not configured"}</div>
            </div>
            <span className={`status-tag ${process.env.RESEND_API_KEY ? "status-success" : "status-warning"}`}>
              {process.env.RESEND_API_KEY ? "Ready" : "No API key"}
            </span>
          </div>
          <div className="data-row">
            <div>
              <strong>Realtime Events</strong>
              <div className="muted" style={{ fontSize: 13 }}>Server-Sent Events</div>
            </div>
            <span className="status-tag status-success">Active</span>
          </div>
        </div>
      </section>
      </div>
    </div>
  );
}
