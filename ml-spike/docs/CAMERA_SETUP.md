# Camera Connection via go2rtc

This guide explains how to connect to a Hikvision camera through HikConnect cloud using go2rtc, without port forwarding.

## Prerequisites

- HikConnect account with camera already added
- Camera serial number and verification code
- Windows PC

## Step 1: Find Camera Info

In HikConnect app:
1. Go to camera → **Settings** → **Device Information**
2. Copy **Serial Number** (e.g., `FC1866068`)
3. Copy **Verification Code** (e.g., `winservice`)

## Step 2: Download go2rtc

Download the latest Windows release from:
https://github.com/AlexxIT/go2rtc/releases/latest

Get `go2rtc_windows_amd64.zip`, extract `go2rtc.exe` into the `ml-spike/` folder.

## Step 3: Configure go2rtc

Edit `ml-spike/go2rtc.yaml`:

```yaml
streams:
  camera1:
    - hikconnect://YOUR_SERIAL:YOUR_VERIFICATION_CODE

api:
  origin: "*"
  listen: ":1985"

rtsp:
  listen: ":8557"

webrtc:
  listen: ":8556"
```

Replace `YOUR_SERIAL` and `YOUR_VERIFICATION_CODE` with your actual values.

## Step 4: Run go2rtc

```bash
cd ml-spike
./go2rtc.exe -config go2rtc.yaml
```

Expected output:
```
INF [api] listen addr=:1985
INF [rtsp] listen addr=:8557
INF [webrtc] listen addr=:8556
```

## Step 5: Verify Stream

Open http://127.0.0.1:1985 in your browser. You should see the camera feed.

The RTSP URL for the inference service is:
```
rtsp://127.0.0.1:8557/camera1
```

## Step 6: Connect Inference Service

Set the environment variable:
```
RTSP_STREAM_URL=rtsp://127.0.0.1:8557/camera1
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `bind: Only one usage of each socket address` | Change ports in `go2rtc.yaml` or run `taskkill /F /IM go2rtc.exe` |
| `command not found` | Use `./go2rtc.exe` instead of `go2rtc.exe` |
| Stream not loading in browser | Check serial and verification code are correct |
| Camera shows offline in go2rtc | Ensure HikConnect app shows camera as online |

## Architecture

```
Camera → HikConnect Cloud → go2rtc → RTSP stream → Inference Service
```

go2rtc acts as a bridge between HikConnect's cloud P2P protocol and a local RTSP stream that the inference service can consume.
