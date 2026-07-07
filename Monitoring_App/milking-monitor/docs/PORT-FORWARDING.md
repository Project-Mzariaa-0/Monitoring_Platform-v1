# Port Forwarding Guide for HikConnect Cameras

This guide explains how to configure port forwarding so the Milking Monitor platform can access your HikConnect camera's RTSP stream from a different network.

## Prerequisites

- Access to the router at the camera's location (admin credentials)
- The camera's local IP address (from HikConnect app)
- The router's public IP address

## Step 1: Find the Camera's Local IP

1. Open the **Hik-Connect** app on your phone
2. Select the camera → tap **Settings** (gear icon)
3. Go to **Device Information** or **Network Settings**
4. Look for **IPv4 Address** (e.g., `192.168.1.100`)
5. Write this down

**Alternative method:**
1. Open a browser on a computer connected to the same network
2. Go to `http://192.168.1.x` (try common ranges: `192.168.1.x` or `192.168.0.x`)
3. The Hikvision camera login page will appear if you find the right IP

## Step 2: Find the Router's Public IP

From a computer on the **same network** as the camera:
```
# Windows PowerShell
(Invoke-WebRequest -Uri "https://api.ipify.org").Content

# Or visit https://whatismyipaddress.com in a browser
```

Write down the public IP (e.g., `123.45.67.89`).

## Step 3: Access the Router Admin Panel

1. Find the router's **local IP** (gateway):
   - Open Command Prompt: `ipconfig`
   - Look for **Default Gateway** (e.g., `192.168.1.1`)
2. Open a browser → go to `http://<gateway_ip>` (e.g., `http://192.168.1.1`)
3. Login with admin credentials
   - Usually on a sticker on the router
   - Common defaults: `admin/admin` or `admin/password`

## Step 4: Configure Port Forwarding

The setting location varies by router brand:

### TP-Link
```
Advanced → NAT Forwarding → Virtual Server → Add
```

### Huawei
```
More Functions → Network → Port Forwarding → Add Rule
```

### D-Link
```
Advanced → Port Forwarding → Add Rule
```

### MikroTik
```
IP → Firewall → NAT → Add New
```

### Generic Routers
Look for: **Port Forwarding**, **Virtual Server**, or **NAT Forwarding**

## Step 5: Add the Port Forwarding Rule

Fill in the form with these values:

| Field | Value |
|-------|-------|
| **Service Name** | `RTSP Camera` or `Hikvision RTSP` |
| **Protocol** | `TCP` |
| **External/WAN Port** | `554` |
| **Internal/LAN IP** | Camera's local IP (e.g., `192.168.1.100`) |
| **Internal/LAN Port** | `554` |

> **Note:** If port 554 doesn't work (ISP blocking), try port `8554` instead.

Click **Save** or **Apply**.

## Step 6: Test the Connection

From your development machine (different network), run:

```powershell
# Test if port is reachable
Test-NetConnection -ComputerName <PUBLIC_IP> -Port 554
```

Expected output:
```
ComputerName     : 123.45.67.89
RemotePort       : 554
TcpTestSucceeded : True
```

If `TcpTestSucceeded: False`, check:
- Camera is powered on and connected to network
- Port forwarding rule is saved and enabled
- ISP isn't blocking port 554 (try 8554)
- Firewall on the router isn't blocking the traffic

## Step 7: Update the Milking Monitor Config

Once port forwarding works, update these files:

### `apps/go2rtc/go2rtc.yaml`
```yaml
streams:
  camera1: rtsp://admin:password@<PUBLIC_IP>:554/Streaming/Channels/101
```

### `apps/inference-service/.env`
```env
RTSP_STREAM_URL=rtsp://admin:password@<PUBLIC_IP>:554/Streaming/Channels/101
```

Replace:
- `<PUBLIC_IP>` → your router's public IP
- `admin` → camera's RTSP username
- `password` → camera's RTSP password

## Step 8: Restart Services

```bash
docker compose restart go2rtc inference-service
```

## Troubleshooting

### Camera not reachable from local network
- Verify the camera is on and connected via Hik-Connect app
- Check if the camera's IP is in the same subnet as the router
- Try pinging the camera from a local computer: `ping 192.168.1.100`

### Port forwarding not working
- Double-check the camera's local IP hasn't changed (use DHCP reservation)
- Make sure no other rule conflicts with port 554
- Check if the router has a "SPI Firewall" or "DoS Protection" — disable temporarily for testing
- Some ISPs block common ports — contact them or use port 8554

### RTSP connection fails but port is open
- Verify RTSP credentials (username/password)
- Try the RTSP URL in VLC media player: `rtsp://admin:password@<PUBLIC_IP>:554/Streaming/Channels/101`
- Check if the camera requires authentication digest (some HiKvision models)

### HikConnect Camera RTSP URLs
| Stream | URL |
|--------|-----|
| Main Stream (HD) | `rtsp://admin:password@<IP>:554/Streaming/Channels/101` |
| Sub-Stream (SD) | `rtsp://admin:password@<IP>:554/Streaming/Channels/102` |

## Security Notes

- **Change default credentials** on the camera (admin/password is insecure)
- Consider using a **non-standard external port** (e.g., `1554` instead of `554`)
- Enable **router firewall** after testing is complete
- Only forward port 554 — don't forward the web interface port (80/443) unless needed
- Regularly update camera firmware for security patches

## Alternative: VPN Access

If port forwarding isn't possible (CGNAT, restrictive ISP), consider:
- **WireGuard** or **OpenVPN** on the camera's network router
- **Tailscale** — zero-config VPN (easiest setup)
- **Cloudflare Tunnel** — free, no port forwarding needed

These options provide secure access without exposing ports to the public internet.
