# Production Operations Runbook

## Service health

Run from `Monitoring_App/milking-monitor`:

```bash
docker compose -f docker-compose.prod.yml ps
curl -fsS http://localhost:8001/health
curl -fsS http://localhost:1984/api/streams
curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:3000/
```

The dashboard's **Equipment** page shows inference readiness, uptime, active inference sessions, database-backed session counts, and model health. The **Alerts** page shows database, inference, model-confidence, and compliance alerts.

## Stream loss

1. Check `docker compose -f docker-compose.prod.yml logs --tail=200 inference-service`.
2. Check go2rtc streams with `curl http://localhost:1984/api/streams`.
3. Verify the RTSP URL and camera reachability from the inference container.
4. Restart go2rtc first, then inference:

```bash
docker compose -f docker-compose.prod.yml restart go2rtc
docker compose -f docker-compose.prod.yml restart inference-service
```

5. Confirm `/health` is ready and run a short monitored session before resuming normal operation.

## Database outage

1. Check PostgreSQL health:

```bash
docker compose -f docker-compose.prod.yml exec postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

2. Inspect logs: `docker compose -f docker-compose.prod.yml logs --tail=200 postgres`.
3. Do not delete the `postgres_data` volume during recovery.
4. Restart PostgreSQL and wait for its healthcheck before restarting web and inference.
5. Reconcile any events emitted during the outage using the inference logs and event contract version.

## Model degradation

If the Alerts page reports low confidence:

1. Record the affected task IDs and time window.
2. Preserve the benchmark input and model version.
3. Compare against the validation benchmark with `python -m src.evaluation.benchmark`.
4. Do not lower thresholds in production without a benchmark report and an approved change.

## Incident evidence

Collect:

```bash
docker compose -f docker-compose.prod.yml logs --no-color --since=1h > incident-logs.txt
curl -fsS http://localhost:8001/health > inference-health.json
curl -fsS http://localhost:1984/api/streams > go2rtc-streams.json
```

Keep the request/correlation ID when investigating an event across inference and web logs.
