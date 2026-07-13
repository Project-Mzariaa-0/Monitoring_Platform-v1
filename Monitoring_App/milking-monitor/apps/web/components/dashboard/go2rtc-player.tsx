"use client";

import { useEffect, useRef, useState, useCallback } from "react";

type Go2rtcStream = {
  name: string;
  source: string;
  api_url: string;
  webrtc_url: string;
  mse_url: string;
  mjpeg_url: string;
  hls_url: string;
};

type Props = {
  src?: string;
  fallbackSrc?: string;
  className?: string;
  style?: React.CSSProperties;
};

const CONNECT_TIMEOUT_MS = 8000;

export default function Go2rtcPlayer({ src = "camera1", fallbackSrc, className, style }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const fallbackVideoRef = useRef<HTMLVideoElement>(null);
  const [status, setStatus] = useState<"loading" | "connected" | "fallback" | "error">("loading");
  const [streamInfo, setStreamInfo] = useState<Go2rtcStream | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const connectedRef = useRef(false);
  const cancelledRef = useRef(false);

  const cleanup = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (pcRef.current) {
      pcRef.current.close();
      pcRef.current = null;
    }
  }, []);

  const activateFallback = useCallback(() => {
    if (cancelledRef.current) return;
    connectedRef.current = true;
    cleanup();
    setStatus("fallback");
  }, [cleanup]);

  useEffect(() => {
    let cancelled = false;
    cancelledRef.current = false;
    connectedRef.current = false;

    async function connect() {
      try {
        setStatus("loading");

        const res = await fetch(`/api/go2rtc?src=${src}`);
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.error || "Failed to get stream info");
        }

        if (cancelled) return;

        const info: Go2rtcStream = await res.json();
        setStreamInfo(info);

        const pc = new RTCPeerConnection({
          iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
        });
        pcRef.current = pc;

        pc.addTransceiver("video", { direction: "recvonly" });
        pc.addTransceiver("audio", { direction: "recvonly" });

        pc.ontrack = (event) => {
          if (videoRef.current && event.streams[0]) {
            videoRef.current.srcObject = event.streams[0];
          }
        };

        pc.oniceconnectionstatechange = () => {
          if (cancelled) return;
          const state = pc.iceConnectionState;

          if (state === "connected" || state === "completed") {
            connectedRef.current = true;
            if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null; }
            setStatus("connected");
          } else if ((state === "failed" || state === "disconnected") && !connectedRef.current) {
            activateFallback();
          }
        };

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        const sdpResponse = await fetch(info.webrtc_url, {
          method: "POST",
          headers: { "Content-Type": "application/sdp" },
          body: offer.sdp,
        });

        if (!sdpResponse.ok) {
          throw new Error(`go2rtc WebRTC handshake failed: ${sdpResponse.status}`);
        }

        const answerSdp = await sdpResponse.text();
        if (cancelled) return;

        await pc.setRemoteDescription(new RTCSessionDescription({
          type: "answer",
          sdp: answerSdp,
        }));

        // Timeout: if not connected within CONNECT_TIMEOUT_MS, fall back
        timerRef.current = setTimeout(() => {
          if (cancelled) return;
          if (!connectedRef.current) {
            activateFallback();
          }
        }, CONNECT_TIMEOUT_MS);

      } catch (err) {
        if (cancelled) return;
        activateFallback();
      }
    }

    connect();

    return () => {
      cancelled = true;
      cancelledRef.current = true;
      cleanup();
    };
  }, [src, cleanup, activateFallback]);

  function handleReconnect() {
    cancelledRef.current = true;
    cleanup();
    connectedRef.current = false;
    setStatus("loading");
    setErrorMsg("");
    setStreamInfo(null);
    cancelledRef.current = false;

    // Try live stream again
    async function connect() {
      try {
        const res = await fetch(`/api/go2rtc?src=${src}`);
        if (!res.ok) throw new Error("Stream unavailable");

        const info: Go2rtcStream = await res.json();
        setStreamInfo(info);

        const pc = new RTCPeerConnection({
          iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
        });
        pcRef.current = pc;

        pc.addTransceiver("video", { direction: "recvonly" });
        pc.addTransceiver("audio", { direction: "recvonly" });

        pc.ontrack = (event) => {
          if (videoRef.current && event.streams[0]) {
            videoRef.current.srcObject = event.streams[0];
          }
        };

        pc.oniceconnectionstatechange = () => {
          const state = pc.iceConnectionState;
          if (state === "connected" || state === "completed") {
            connectedRef.current = true;
            if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null; }
            setStatus("connected");
          } else if ((state === "failed" || state === "disconnected") && !connectedRef.current) {
            activateFallback();
          }
        };

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        const sdpResponse = await fetch(info.webrtc_url, {
          method: "POST",
          headers: { "Content-Type": "application/sdp" },
          body: offer.sdp,
        });

        if (!sdpResponse.ok) throw new Error("WebRTC handshake failed");

        const answerSdp = await sdpResponse.text();
        await pc.setRemoteDescription(new RTCSessionDescription({ type: "answer", sdp: answerSdp }));

        timerRef.current = setTimeout(() => {
          if (!connectedRef.current) activateFallback();
        }, CONNECT_TIMEOUT_MS);

      } catch {
        activateFallback();
      }
    }

    connect();
  }

  const showVideo = status === "connected" || status === "fallback";
  const showFallbackVideo = status === "fallback";

  return (
    <div className={className} style={{ position: "relative", ...style }}>
      {/* Live WebRTC video */}
      <video
        ref={videoRef}
        autoPlay
        muted
        playsInline
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          borderRadius: 10,
          background: "#1a1a1a",
          display: showVideo && !showFallbackVideo ? "block" : "none",
        }}
      />

      {/* Fallback HTML5 video */}
      {showFallbackVideo && (
        <video
          ref={fallbackVideoRef}
          autoPlay
          muted
          loop
          playsInline
          src="/fallback.mp4"
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            borderRadius: 10,
            background: "#1a1a1a",
          }}
        />
      )}

      {status === "loading" && (
        <div style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "rgba(0,0,0,0.5)",
          borderRadius: 10,
          color: "#fff",
          fontSize: 14,
          fontWeight: 600,
        }}>
          Connecting to {src}...
        </div>
      )}

      {status === "connected" && (
        <div style={{
          position: "absolute",
          top: 10,
          left: 10,
          display: "flex",
          alignItems: "center",
          gap: 6,
          padding: "4px 10px",
          borderRadius: 999,
          background: "rgba(0,0,0,0.55)",
          backdropFilter: "blur(8px)",
          color: "#fff",
          fontSize: 11,
          fontWeight: 600,
        }}>
          <span style={{
            width: 6,
            height: 6,
            borderRadius: 999,
            background: "#4ade80",
            animation: "breathe 2.4s ease-in-out infinite",
          }} />
          LIVE
        </div>
      )}

      {status === "fallback" && (
        <div style={{
          position: "absolute",
          top: 10,
          left: 10,
          display: "flex",
          alignItems: "center",
          gap: 6,
          padding: "4px 10px",
          borderRadius: 999,
          background: "rgba(0,0,0,0.55)",
          backdropFilter: "blur(8px)",
          color: "#fff",
          fontSize: 11,
          fontWeight: 600,
        }}>
          <span style={{
            width: 6,
            height: 6,
            borderRadius: 999,
            background: "#facc15",
            animation: "breathe 2.4s ease-in-out infinite",
          }} />
          FALLBACK
        </div>
      )}

      {status === "error" && (
        <div style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 12,
          background: "rgba(0,0,0,0.7)",
          borderRadius: 10,
          color: "#fff",
          textAlign: "center",
          padding: 20,
        }}>
          <div style={{ fontSize: 14, fontWeight: 600 }}>Stream unavailable</div>
          <div style={{ fontSize: 12, opacity: 0.7, maxWidth: 280 }}>{errorMsg}</div>
          <button
            onClick={handleReconnect}
            style={{
              padding: "8px 16px",
              borderRadius: 999,
              border: "1px solid rgba(255,255,255,0.3)",
              background: "transparent",
              color: "#fff",
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Retry
          </button>
        </div>
      )}

      {streamInfo && (
        <div style={{
          position: "absolute",
          bottom: 10,
          right: 10,
          padding: "4px 10px",
          borderRadius: 999,
          background: "rgba(0,0,0,0.55)",
          backdropFilter: "blur(8px)",
          color: "rgba(255,255,255,0.7)",
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: "0.04em",
          textTransform: "uppercase",
        }}>
          {streamInfo.name}
        </div>
      )}
    </div>
  );
}
