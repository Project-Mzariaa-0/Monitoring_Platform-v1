"""Test go2rtc connection and provide RTSP URL for the inference pipeline."""

import httpx
import sys


def test_connection(go2rtc_url: str = "http://127.0.0.1:1984"):
    try:
        r = httpx.get(f"{go2rtc_url}/api/streams", timeout=5)
        streams = r.json()
        print("Active streams:")
        for name, info in streams.items():
            print(f"  {name}: {info}")
        print(f"\nRTSP URL: rtsp://127.0.0.1:8555/camera1")
        print(f"Web UI: {go2rtc_url}")
        return True
    except Exception as e:
        print(f"Cannot connect to go2rtc: {e}")
        print("Make sure go2rtc is running.")
        return False


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:1984"
    test_connection(url)
