"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

export default function EmailSignUpForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [registered, setRegistered] = useState(false);
  const [emailWarning, setEmailWarning] = useState<string | null>(null);
  const [resending, setResending] = useState(false);
  const [resentMessage, setResentMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);

    try {
      const registration = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, name }),
      });
      const registrationBody = await registration.json().catch(() => null);
      if (!registration.ok) {
        const validationDetails = registrationBody?.details as Record<string, string[]> | undefined;
        const firstValidationError = validationDetails
          ? Object.values(validationDetails).flat()[0]
          : undefined;
        setError(firstValidationError ?? registrationBody?.error ?? "Sign-up failed. Please check your details.");
        return;
      }

      if (registrationBody?.verificationEmailSent === false) {
        setEmailWarning(
          registrationBody?.verificationError
            ? `Account created, but the verification email failed: ${registrationBody.verificationError}. Use Resend below.`
            : "Account created, but the verification email could not be sent. Use Resend below.",
        );
      } else {
        setEmailWarning(null);
      }
      setRegistered(true);
    } catch (caught: any) {
      setError(caught?.message ?? "An unexpected error occurred.");
    } finally {
      setPending(false);
    }
  }

  async function resendEmail() {
    setResending(true);
    setResentMessage(null);
    try {
      const response = await fetch("/api/auth/resend-verification", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const payload = await response.json().catch(() => null);
      setResentMessage(response.ok ? "Verification email sent. Check your inbox." : (payload?.error ?? "Resend failed."));
    } catch {
      setResentMessage("Could not reach the server.");
    } finally {
      setResending(false);
    }
  }

  if (registered) {
    return (
      <div className="auth-form">
        <div className="status-tag status-success">Account created</div>
        <h2 className="section-title" style={{ margin: "12px 0 8px" }}>
          Check your inbox
        </h2>
        <p className="muted" style={{ margin: 0 }}>
          We sent a verification link to <strong>{email}</strong>. Click it within 24 hours to activate your login,
          then sign in.
        </p>
        {emailWarning ? <div className="auth-error">{emailWarning}</div> : null}
        <button className="button button-secondary" type="button" onClick={resendEmail} disabled={resending}>
          {resending ? "Sending…" : "Resend verification email"}
        </button>
        {resentMessage ? <p className="muted" style={{ margin: 0, fontSize: 13 }}>{resentMessage}</p> : null}
        <p className="muted" style={{ margin: 0, fontSize: 13 }}>
          <Link className="auth-link" href="/sign-in">Go to sign in</Link>
        </p>
      </div>
    );
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <div>
        <label className="label" htmlFor="name">
          Full name
        </label>
        <input
          id="name"
          className="input"
          type="text"
          autoComplete="name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
          minLength={2}
          maxLength={120}
          placeholder="Nora Smith"
        />
      </div>
      <div>
        <label className="label" htmlFor="email">
          Work email
        </label>
        <input
          id="email"
          className="input"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
          placeholder="nora.smith@farm.com"
        />
      </div>
      <div>
        <label className="label" htmlFor="password">
          Password
        </label>
        <input
          id="password"
          className="input"
          type="password"
          autoComplete="new-password"
          minLength={12}
          maxLength={128}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
          aria-describedby="password-hint"
        />
        <p className="muted" id="password-hint" style={{ margin: "6px 0 0", fontSize: 12 }}>
          At least 12 characters, up to 128.
        </p>
      </div>
      {error ? <div className="auth-error">{error}</div> : null}
      <button className="button button-primary" type="submit" disabled={pending}>
        {pending ? "Creating account..." : "Create account"}
      </button>
      <p className="muted" style={{ margin: 0, fontSize: 13 }}>
        Already have an account? <Link className="auth-link" href="/sign-in">Sign in</Link>
      </p>
    </form>
  );
}
