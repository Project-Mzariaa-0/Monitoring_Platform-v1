import Link from "next/link";

const TYPE_META: Record<string, { label: string; className: string; hint: string }> = {
  unauthorized: {
    label: "Session expired",
    className: "status-warning",
    hint: "Your session is missing or expired. Sign in again to continue.",
  },
  forbidden: {
    label: "Not allowed",
    className: "status-danger",
    hint: "Your account is not allowed to perform this action.",
  },
  "not-found": {
    label: "Not found",
    className: "status-neutral",
    hint: "The requested item does not exist or was removed.",
  },
  "rate-limited": {
    label: "Too many requests",
    className: "status-warning",
    hint: "You hit a rate limit. Wait a minute, then try again.",
  },
  validation: {
    label: "Invalid request",
    className: "status-warning",
    hint: "The request was rejected. Check the highlighted fields and retry.",
  },
  "server-error": {
    label: "Server error",
    className: "status-danger",
    hint: "Something went wrong on our side. Try again, and contact support if it persists.",
  },
  network: {
    label: "Connection failed",
    className: "status-danger",
    hint: "The app could not reach the server. Check your connection and retry.",
  },
};

export default async function ErrorPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; type?: string; message?: string; from?: string }>;
}) {
  const params = await searchParams;
  const status = Number(params.status) || 0;
  const meta = TYPE_META[params.type ?? ""] ?? TYPE_META["server-error"];
  const message = (params.message || "An unexpected error occurred.").slice(0, 300);
  const from = params.from || "/";

  return (
    <div className="page-grid" style={{ maxWidth: 640, margin: "48px auto" }}>
      <section className="card card-pad" style={{ textAlign: "center" }}>
        <span className={`status-tag ${meta.className}`}>{meta.label}</span>
        <h1 className="section-title" style={{ fontSize: 40, margin: "16px 0 4px" }}>
          {status === 0 ? "—" : status}
        </h1>
        <p style={{ fontWeight: 700, margin: "0 0 8px" }}>{message}</p>
        <p className="muted" style={{ margin: "0 0 4px" }}>
          {meta.hint}
        </p>
        {from !== "/" ? (
          <p className="muted" style={{ fontSize: 12, margin: "0 0 16px" }}>
            While opening: {from}
          </p>
        ) : null}
        <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap", marginTop: 16 }}>
          {params.type === "unauthorized" ? (
            <Link className="button button-primary" href={`/sign-in?callbackUrl=${encodeURIComponent(from)}`}>
              Sign in again
            </Link>
          ) : (
            <Link className="button button-primary" href={from}>
              Try again
            </Link>
          )}
          <Link className="button button-secondary" href="/">
            Back to dashboard
          </Link>
        </div>
      </section>
    </div>
  );
}
