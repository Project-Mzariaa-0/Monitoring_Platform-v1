"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export default function VerifyEmailClient({ email, token }: { email: string; token: string }) {
  const linkComplete = Boolean(email && token);
  const [status, setStatus] = useState<"pending" | "success" | "error">(() => (linkComplete ? "pending" : "error"));
  const [message, setMessage] = useState(() =>
    linkComplete ? "Verifying your email…" : "This verification link is incomplete.",
  );
  const [resending, setResending] = useState(false);
  const [resentMessage, setResentMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!linkComplete) return;
    let cancelled = false;
    fetch("/api/auth/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, token }),
    })
      .then(async (response) => {
        const payload = await response.json().catch(() => null);
        if (cancelled) return;
        if (response.ok) {
          setStatus("success");
          setMessage("Your email is verified. You can now sign in.");
        } else {
          setStatus("error");
          setMessage(payload?.error ?? "Verification failed.");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStatus("error");
          setMessage("Could not reach the server. Check your connection and retry.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [email, token, linkComplete]);

  async function resend() {
    setResending(true);
    setResentMessage(null);
    try {
      const response = await fetch("/api/auth/resend-verification", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const payload = await response.json().catch(() => null);
      setResentMessage(response.ok ? "New link sent. Check your inbox." : (payload?.error ?? "Resend failed."));
    } catch {
      setResentMessage("Could not reach the server.");
    } finally {
      setResending(false);
    }
  }

  return (
    <div className="page-grid" style={{ maxWidth: 560, margin: "48px auto" }}>
      <section className="card card-pad" style={{ textAlign: "center" }}>
        <span className={`status-tag ${status === "success" ? "status-success" : status === "error" ? "status-danger" : "status-neutral"}`}>
          {status === "success" ? "Verified" : status === "error" ? "Failed" : "Verifying"}
        </span>
        <h1 className="section-title" style={{ fontSize: 26, margin: "16px 0 8px" }}>
          Email verification
        </h1>
        <p className="muted" style={{ margin: "0 0 16px" }}>{message}</p>
        {status === "success" ? (
          <Link className="button button-primary" href="/sign-in">
            Sign in
          </Link>
        ) : status === "error" ? (
          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <button className="button button-primary" type="button" onClick={resend} disabled={resending || !email}>
              {resending ? "Sending…" : "Resend link"}
            </button>
            <Link className="button button-secondary" href="/sign-in">
              Back to sign in
            </Link>
          </div>
        ) : null}
        {resentMessage ? <p className="muted" style={{ marginTop: 12 }}>{resentMessage}</p> : null}
      </section>
    </div>
  );
}
