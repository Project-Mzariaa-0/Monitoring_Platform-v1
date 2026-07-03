"use client";

import { signIn } from "next-auth/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

export default function EmailSignUpForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);

    try {
      const result = await signIn("credentials", {
        email,
        password,
        redirect: false,
        callbackUrl: "/",
      });

      if (result?.error) {
        setError("Sign-up failed. Please check your details.");
      } else {
        router.push("/");
        router.refresh();
      }
    } catch (caught: any) {
      setError(caught?.message ?? "An unexpected error occurred.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
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
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
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
