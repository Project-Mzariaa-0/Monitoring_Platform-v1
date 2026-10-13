"use client";

import Link from "next/link";

export default function RootError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="page-grid" style={{ maxWidth: 640, margin: "48px auto" }}>
      <section className="card card-pad" style={{ textAlign: "center" }}>
        <span className="status-tag status-danger">Something went wrong</span>
        <h1 className="section-title" style={{ fontSize: 28, margin: "16px 0 4px" }}>
          This view crashed
        </h1>
        <p className="muted" style={{ margin: "0 0 16px" }}>
          {error.message || "An unexpected rendering error occurred."}
        </p>
        <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
          <button className="button button-primary" type="button" onClick={reset}>
            Try again
          </button>
          <Link className="button button-secondary" href="/">
            Back to dashboard
          </Link>
        </div>
      </section>
    </div>
  );
}
