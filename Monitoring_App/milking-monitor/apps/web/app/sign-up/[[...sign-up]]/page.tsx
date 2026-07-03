import Link from "next/link";
import EmailSignUpForm from "../../../components/auth/email-sign-up-form";

export default function SignUpPage() {
  return (
    <div className="auth-shell">
      <section className="auth-pane">
        <Link className="brand" href="/" style={{ marginBottom: 48, padding: 0 }}>
          <span className="brand-mark">M</span>
          <span className="brand-name" style={{ color: "var(--text-primary)" }}>
            Milking Monitor
          </span>
        </Link>
        <h1 className="page-title" style={{ marginBottom: 8 }}>
          Get started
        </h1>
        <p className="muted" style={{ marginTop: 0, marginBottom: 28 }}>
          Create a supervisor account for your compliance monitoring unit.
        </p>
        <EmailSignUpForm />
      </section>
      <section className="auth-visual">
        <div className="auth-headline">Build a complete audit trail from every session.</div>
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
