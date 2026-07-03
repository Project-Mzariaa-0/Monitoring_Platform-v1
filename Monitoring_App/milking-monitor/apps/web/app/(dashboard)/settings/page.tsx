import Link from "next/link";
import { getServerSession } from "next-auth/next";
import { authOptions } from "../../lib/auth/options";

export default async function SettingsPage() {
  const session = await getServerSession(authOptions);
  const user = session?.user;
  const name = user?.name || user?.email || "Guest";
  const initials = user?.name
    ? user.name.split(" ").map((n) => n[0]).join("").substring(0, 2).toUpperCase()
    : user?.email
    ? user.email.substring(0, 2).toUpperCase()
    : "??";

  return (
    <div className="grid-2">
      <section className="card card-pad">
        <h2 className="section-title">Supervisor Profile</h2>
        <div className="profile-card" style={{ background: "#fff", color: "var(--text-primary)", borderColor: "var(--border)", display: "flex", alignItems: "center", gap: 12 }}>
          <span className="avatar">{initials}</span>
          <span>
            <strong style={{ display: "block" }}>{name}</strong>
            <span className="small-muted">Unit Supervisor</span>
          </span>
        </div>
        <Link className="button button-secondary" href="/settings/patient" style={{ marginTop: 16 }}>
          Patient/Herd Settings
        </Link>
      </section>

      <section className="card card-pad">
        <h2 className="section-title">Clinical Threshold</h2>
        <label className="label">Exception sensitivity</label>
        <input className="input" type="range" min="20" max="60" defaultValue="32" />
        <div className="data-row">
          <span>Notification stream</span>
          <span className="status-tag status-success">
            <span className="live-dot" />
            Enabled
          </span>
        </div>
        <div className="data-row">
          <span>Critical alert escalation</span>
          <span className="status-tag status-success">Live</span>
        </div>
      </section>
    </div>
  );
}
