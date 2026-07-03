import Link from "next/link";
import EmailSignInForm from "../../../components/auth/email-sign-in-form";

export default function SignInPage() {
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
          Welcome back
        </h1>
        <p className="muted" style={{ marginTop: 0, marginBottom: 28 }}>
          Sign in to supervise compliance windows, alerts, and operator performance.
        </p>
        <EmailSignInForm />
      </section>
      <section className="auth-visual">
        <div className="auth-headline">Realtime compliance for every milking position.</div>
        <div className="floating-score">
          <span className="label" style={{ color: "#c7cdd9" }}>
            Live compliance score
          </span>
          <div className="metric" style={{ color: "var(--accent-bright)", margin: "10px 0" }}>
            96%
          </div>
          <span className="status-pill status-success">Optimal</span>
        </div>
      </section>
    </div>
  );
}
