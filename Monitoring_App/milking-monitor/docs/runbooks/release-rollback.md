# Release and Rollback Runbook

## Preconditions

- CI is green on the exact commit to release.
- Production Compose configuration validates with `docker compose -f docker-compose.prod.yml config --quiet`.
- Database backup or an approved recovery point exists.
- Required secrets are present in the deployment environment.

## Release

From `Monitoring_App/milking-monitor`:

```bash
git fetch --tags
git checkout <release-commit>
docker compose -f docker-compose.prod.yml build web inference-service
docker compose -f docker-compose.prod.yml run --rm web npm run drizzle:migrate
docker compose -f docker-compose.prod.yml up -d
```

Verify:

```bash
docker compose -f docker-compose.prod.yml ps
curl -fsS http://localhost:8001/health
curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:3000/
```

Open the Equipment and Alerts pages and confirm service readiness, database connectivity, stream state, and model health before starting a monitored session.

## Rollback

1. Stop new session creation and record the incident/correlation ID.
2. Preserve logs and the current database backup.
3. Check out the last known-good commit.
4. Rebuild only the affected application image and restart the stack:

```bash
git checkout <known-good-commit>
docker compose -f docker-compose.prod.yml build web inference-service
docker compose -f docker-compose.prod.yml up -d
```

5. Do not automatically roll back database migrations. If a migration is incompatible, use a reviewed forward migration or restore the database to the approved recovery point.
6. Verify health endpoints, dashboard alerts, event ingestion, and a controlled test session.

## Completion criteria

- All service healthchecks are healthy.
- No new critical Alerts are present.
- A test event appears once in the dashboard and audit trail.
- The release or rollback commit, operator, timestamps, and evidence files are recorded.
