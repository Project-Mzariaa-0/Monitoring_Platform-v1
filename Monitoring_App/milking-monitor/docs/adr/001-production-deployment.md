# ADR 001: Production Deployment Architecture

- Status: Accepted
- Date: 2026-09-22
- Owners: Platform team

## Context

The development Compose file mounts the source tree and installs dependencies at container startup. That is useful locally but creates non-reproducible deployments, slow restarts, and accidental coupling between source changes and running services.

## Decision

Production deployments use `docker-compose.prod.yml` with:

- Multi-stage Next.js standalone image builds.
- A pinned Python runtime image with dependencies installed during image build.
- No source-code bind mounts.
- Restart policies for stateful and application services.
- Healthchecks and `depends_on` health conditions for PostgreSQL, go2rtc, inference, and web.
- Environment values supplied through deployment secrets and `.env` files, never committed credentials.
- PostgreSQL data stored in a named persistent volume.

Development continues to use `docker-compose.yml` and source mounts.

## Consequences

Production images must be rebuilt for code changes. Database migrations must run before or as part of a release procedure. Secrets and camera URLs are deployment-owned configuration. The production Compose file is validated in CI before release.

## Rejected alternatives

- Running `npm install` and `npm run dev` in production: non-reproducible and not suitable for failure recovery.
- Sharing the development Compose file: would retain source mounts and public database exposure.
- Kubernetes at this stage: adds operational complexity before the current single-site deployment needs it.
