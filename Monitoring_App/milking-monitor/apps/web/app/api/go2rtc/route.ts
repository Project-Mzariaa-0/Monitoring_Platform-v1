import { NextRequest, NextResponse } from "next/server";

const GO2RTC_URL = process.env.GO2RTC_URL || "http://localhost:1984";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const src = searchParams.get("src") || "camera1";

  try {
    const response = await fetch(`${GO2RTC_URL}/api/streams`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return NextResponse.json({ error: "Failed to reach go2rtc" }, { status: 502 });
    }

    const streams = await response.json();
    const stream = streams[src];

    if (!stream) {
      return NextResponse.json({ error: `Stream '${src}' not found` }, { status: 404 });
    }

    return NextResponse.json({
      name: src,
      source: stream,
      api_url: GO2RTC_URL,
      webrtc_url: `${GO2RTC_URL}/api/webrtc?src=${src}`,
      mse_url: `${GO2RTC_URL}/api/stream.mp4?src=${src}`,
      mjpeg_url: `${GO2RTC_URL}/api/stream.mjpeg?src=${src}`,
      hls_url: `${GO2RTC_URL}/api/stream.m3u8?src=${src}`,
    });
  } catch (error) {
    return NextResponse.json(
      { error: "go2rtc is not reachable", detail: String(error) },
      { status: 502 }
    );
  }
}
