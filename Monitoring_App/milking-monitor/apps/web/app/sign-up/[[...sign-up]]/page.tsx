import Link from "next/link";
import EmailSignUpForm from "../../../components/auth/email-sign-up-form";
import { AuthFeatures } from "../../../components/auth/auth-features";

export default function SignUpPage() {
  return (
    <div className="auth-shell">
      <section className="auth-pane">
        <Link className="brand" href="/" style={{ padding: 0, alignSelf: "center", marginTop: 24, marginBottom: "auto" }}>
          <img src="/logo12.png" alt="Milking Monitor" className="brand-logo brand-logo-auth" />
        </Link>
        <div style={{ marginBottom: "auto", marginTop: -120, width: "100%", maxWidth: 420, alignSelf: "center" }}>
          <h1 className="page-title" style={{ marginBottom: 8 }}>
            Get started
          </h1>
          <p className="muted" style={{ marginTop: 0, marginBottom: 28 }}>
            Create a supervisor account for your compliance monitoring unit.
          </p>
          <EmailSignUpForm />
        </div>
      </section>
      <section className="auth-visual">
        <div style={{ position: "relative", zIndex: 2, width: "100%", display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="auth-headline">Build a complete audit trail from every session.</div>
          <AuthFeatures />
        </div>
        <div className="floating-score">
          <span className="label" style={{ color: "#c7cdd9" }}>
            Unit readiness
          </span>
          <div className="metric" style={{ color: "#F7F5EF", margin: "10px 0" }}>
            98%
          </div>
          <span className="status-tag status-success">Ready</span>
        </div>
      </section>
    </div>
  );
}
