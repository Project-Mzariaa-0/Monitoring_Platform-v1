"use client";

import { useEffect, useState } from "react";

type LiveEvent = {
  session_id: string;
  type: string;
  payload: Record<string, unknown>;
};

export default function LiveSessionStream({ sessionId, initialEvents = [] }: { sessionId: string; initialEvents?: LiveEvent[] }) {
  const [events, setEvents] = useState<LiveEvent[]>(initialEvents);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const source = new EventSource(`/api/ws?session_id=${sessionId}`);

    source.onopen = () => {
      setConnected(true);
    };

    source.onmessage = (message) => {
      const parsed = JSON.parse(message.data) as LiveEvent;
      setEvents((current) => [parsed, ...current].slice(0, 8));
    };

    source.onerror = () => {
      setConnected(false);
    };

    return () => {
      source.close();
    };
  }, [sessionId]);

  return (
    <section className="card card-pad">
      <div className="nav-card" style={{ border: "1px solid var(--border)", borderRadius: 16, marginBottom: 16 }}>
        <div>
          <div style={{ fontWeight: 700 }}>Realtime feed</div>
          <div className="muted" style={{ fontSize: 14 }}>
            {connected ? "Connected" : "Reconnecting"}
          </div>
        </div>
        <span style={{ width: 12, height: 12, borderRadius: 999, background: connected ? "var(--success)" : "var(--danger)" }} />
      </div>

      <div className="page-grid">
        {events.length === 0 ? (
          <div className="muted">Waiting for inference events...</div>
        ) : (
          events.map((event, index) => (
            <article key={`${event.type}-${index}`} className="card card-pad" style={{ background: "#fafafa" }}>
              <div className="muted" style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase" }}>
                {event.type}
              </div>
              <div style={{ marginTop: 8, fontWeight: 700 }}>{event.session_id}</div>
              <pre style={{ margin: 0, marginTop: 8, whiteSpace: "pre-wrap", fontSize: 12, color: "var(--muted)" }}>
                {JSON.stringify(event.payload, null, 2)}
              </pre>
            </article>
          ))
        )}
      </div>
    </section>
  );
}