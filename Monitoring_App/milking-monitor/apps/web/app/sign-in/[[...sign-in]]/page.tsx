import Link from "next/link";
import EmailSignInForm from "../../../components/auth/email-sign-in-form";

export default function SignInPage() {
  return (
    <div className="auth-shell">
      <section className="auth-pane">
        <Link className="brand" href="/" style={{ padding: 0, alignSelf: "center", marginTop: 24, marginBottom: "auto" }}>
          <img src="/logo12.png" alt="Milking Monitor" className="brand-logo brand-logo-auth" />
        </Link>
        <div style={{ marginBottom: "auto", marginTop: -120, width: "100%", maxWidth: 420, alignSelf: "center" }}>
          <h1 className="page-title" style={{ marginBottom: 8 }}>
            Welcome back
          </h1>
          <p className="muted" style={{ marginTop: 0, marginBottom: 28 }}>
            Sign in to supervise compliance windows, alerts, and operator performance.
          </p>
          <EmailSignInForm />
        </div>
      </section>
      <section className="auth-visual">
        <div className="auth-headline">Realtime compliance for every milking position.</div>
        <div className="floating-score">
          <span className="label" style={{ color: "#c7cdd9" }}>
            Live compliance score
          </span>
          <div className="metric" style={{ color: "#F7F5EF", margin: "10px 0" }}>
            96%
          </div>
          <span className="status-tag status-success">Optimal</span>
        </div>
      </section>
    </div>
  );
}
