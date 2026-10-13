import Link from "next/link";

export default function NotFound() {
  return (
    <div className="page-grid" style={{ maxWidth: 640, margin: "48px auto" }}>
      <section className="card card-pad" style={{ textAlign: "center" }}>
        <span className="status-tag status-neutral">Not found</span>
        <h1 className="section-title" style={{ fontSize: 40, margin: "16px 0 4px" }}>
          404
        </h1>
        <p className="muted" style={{ margin: "0 0 16px" }}>
          This page or session does not exist or was removed.
        </p>
        <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
          <Link className="button button-primary" href="/">
            Back to dashboard
          </Link>
          <Link className="button button-secondary" href="/sessions">
            Session history
          </Link>
        </div>
      </section>
    </div>
  );
}
