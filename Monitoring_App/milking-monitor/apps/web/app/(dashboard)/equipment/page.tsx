import EquipmentStatus from "../../../components/dashboard/equipment-status";

export default function EquipmentPage() {
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
  );
}
