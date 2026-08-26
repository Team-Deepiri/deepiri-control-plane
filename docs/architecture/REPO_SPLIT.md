# Repo split: deepiri-platform vs deepiri-control-plane

**Decision (2026-08-26):** the **full monorepo body** lives in **deepiri-control-plane**; **deepiri-platform** is the slim cloud VPS portal.

| Repo | What it is | Compose file |
|------|------------|--------------|
| **`deepiri-control-plane`** | Full local/lab stack (Cyrex, LIS, Kafka, Milvus, speech engine) | **`docker-compose.dev.yml`** (main dev compose) |
| **`deepiri-platform`** | Cloud VPS internal portal only | `docker-compose.yml` |

## GitHub layout

1. **`Team-Deepiri/deepiri-control-plane`** — this repo
2. **`Team-Deepiri/deepiri-platform`** — cloud portal ([PR #304](https://github.com/Team-Deepiri/deepiri-platform/pull/304))

## Cloud services (`docker-compose.yml` in deepiri-platform)

- `postgres-platform`, `redis`, `nginx`, `certbot`
- `auth-service`, `api-gateway`, `jobs`, `registry`, `platform-frontend`, `external-bridge-service`
- `pg-backup-offsite` (optional)

## Control plane (`docker-compose.dev.yml` in this repo)

See `docs/architecture/DATABASES_AND_COMPOSE_BY_PLANE.md`.

Includes **speech engine** (`livekit` + `speech` in compose and `teams/ai-team.yml`).

## Local dev

```bash
git clone git@github.com:Team-Deepiri/deepiri-control-plane.git
cd deepiri-control-plane
bash setup-deepiri-dev.sh
```

Cloud portal deploy uses **deepiri-platform**:
```bash
docker compose -f docker-compose.yml up -d
```
