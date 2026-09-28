# Stretch Goal — Health Check Endpoints (S, 1 point)

> Applies to all three project versions. *Site*, *asset*, and *job* stand in for your version's nouns.

## Summary

`GET /health` already exists and returns `{"status": "ok"}`. It reports that the application process is answering requests — nothing more. It says "ok" with the database stopped, which makes it useless for the failure people actually hit.

This feature keeps that ping as-is and adds two endpoints beside it: a readiness check that tells the truth about whether the application can actually serve requests, and an admin-only detail view that says which dependency is at fault when one isn't.

## Workflow

1. Something calls `/health`. The application answers immediately without touching the database.
2. Something calls `/health/ready`. The application runs a trivial query and reports the database as reachable.
3. The database becomes unreachable. `/health` still returns `200` — the process is fine. `/health/ready` returns `503`.
4. An admin calls `/health/detail` and sees each dependency listed separately, including S3, and can tell at a glance which one is failing.

## Requirements

### Functional Requirements

1. `GET /health` reports process liveness and contacts no dependency; its existing behavior is unchanged
2. `GET /health/ready` verifies database connectivity and reports whether the application is able to serve requests
3. When the database is unavailable, `/health/ready` returns `503` — not `200`, and not `500`
4. `GET /health/detail` reports the database and the S3 bucket separately, each with its own status
5. `GET /health/detail` is restricted to admins; `/health` and `/health/ready` require no authentication
6. A failing dependency check is caught and reported, never surfaced as an unhandled exception
7. The unauthenticated endpoints reveal no connection strings, credentials, hostnames, or bucket names
8. All three behave the same way on the deployed Lambda as they do locally

### Non-Functional Requirements

1. The readiness check uses a trivial query through the existing session dependency, not a real application query
2. Dependency checks are bounded, so an unreachable dependency yields a prompt failure rather than a request that hangs
3. All three endpoints are cheap enough to call repeatedly without appearing in performance measurements
4. Unit tests cover the healthy case, the database-unavailable case, and admin-only access to the detail endpoint

## User Stories

- As a developer, I can tell whether a deployment problem is the application or the database in a single request
- As a developer, I get a `503` from a readiness check when the database is down, not a misleading `200`
- As an admin, I can see which specific dependency is failing rather than only that something is
- As an operator, I can call the basic health endpoints without credentials
- As a reviewer, I can confirm the public endpoints reveal nothing about the infrastructure behind them

## Technical Notes

- Keep `/health` exactly as it is. Being deliberate about which question each endpoint answers is most of the value here
- `SELECT 1` through `Depends(get_db)` is the whole database check. Anything heavier makes the endpoint a liability. For S3, a `head_bucket` call through the existing boto3 client is the equivalent
- The catch-all `Exception` handler in `app/main.py` returns `500` for anything unhandled, which would turn a failed readiness check into a `500` and lose the distinction requirement 3 is asking for. Catch the connectivity error inside the endpoint and return `503` deliberately
- Bounding the checks matters more on Lambda than locally. An unreachable database inside a VPC typically hangs rather than refusing, so without a timeout the readiness endpoint burns the entire function timeout before answering
- The admin guard on `/health/detail` is the existing role dependency — no new mechanism needed
- Resist reporting dependency versions or the database host on the unauthenticated endpoints. It is genuinely useful while debugging and exactly the kind of detail that belongs behind the admin check
- Deciding what belongs in readiness versus detail is the judgment call. The database clearly belongs in readiness. S3 arguably does not — the application is useful without it, and including it means an S3 problem reports the whole application as down

## Definition of Done

- [ ] `GET /health` returns `200` without touching the database, exactly as before
- [ ] `GET /health/ready` returns `200` when the database is reachable
- [ ] With the database stopped, `/health` still returns `200` and `/health/ready` returns `503`
- [ ] A database failure produces a `503`, not a `500` from the catch-all handler
- [ ] An unreachable dependency produces a response promptly rather than hanging
- [ ] `GET /health/detail` reports the database and S3 separately
- [ ] `GET /health/detail` is reachable only by admins; the other two need no token
- [ ] No unauthenticated endpoint reveals credentials, hostnames, or bucket names
- [ ] All three endpoints behave the same on the deployed Lambda as locally
- [ ] Unit tests cover the healthy case, the unavailable case, and admin-only access
- [ ] No regressions to the existing `/health` consumers
