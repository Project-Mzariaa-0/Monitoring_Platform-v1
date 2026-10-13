"use client";

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, minHeight: "100vh", display: "grid", placeItems: "center", background: "#F7F5EF" }}>
        <div style={{ maxWidth: 480, padding: 32, textAlign: "center", background: "#fff", borderRadius: 12 }}>
          <h1 style={{ margin: "0 0 8px" }}>App failed to load</h1>
          <p style={{ color: "#5C6B5D", margin: "0 0 16px" }}>A critical error occurred. Reload to try again.</p>
          <button
            type="button"
            onClick={reset}
            style={{ padding: "10px 24px", borderRadius: 8, border: "none", background: "#1F4D3A", color: "#fff", cursor: "pointer" }}
          >
            Reload
          </button>
        </div>
      </body>
    </html>
  );
}
