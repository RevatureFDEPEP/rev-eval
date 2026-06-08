# W2-F3 — Centralized Log Aggregation (Loki + Promtail + Grafana)

## Context

Day 6 feature from `days_6_10_features.md:55-64`: "Centralized Log Aggregation and Log Shipping." Today each container logs to its own stdout (Docker json-file driver); debugging a cross-service request means tailing multiple terminals with no search, no correlation, no persistence. Acceptance criteria: (1) Grafana + Loki in compose, (2) ship all microservice logs to Loki, (3) standard JSON log formatting utility in the Python services, (4) Grafana dashboard showing nginx request codes, response times, and Python error trace counts.

Current state is rough: gateway hardcodes `basicConfig(INFO)` and mixes `logger` with `print()`; the other 3 services configure no logging at all and use `print()` in `db/session.py`; no `LOG_LEVEL` anywhere.

**Decisions made with user (locked):**
1. **Shipping:** Promtail container + `docker_sd_configs` (Docker socket mount); compose service name → `service` label. No Loki logging driver, no plugin install.
2. **JSON logs:** stdlib-only custom `logging.Formatter` in a `logging_config.py` copied into each service (matches per-service isolation pattern). No new deps.
3. **Correlation:** full `X-Correlation-Id` propagation now (pulls Day 14 spec item forward) — nginx fallback-generates, gateway generates/forwards, services log + propagate on outbound httpx, frontend BFF generates too.
4. **Grafana:** fully provisioned as code (datasource YAML + dashboard JSON in git). Anonymous Viewer auth (`GF_AUTH_ANONYMOUS_ENABLED=true`). Host port **3001** (3000 taken by frontend).
4b. **Separate compose project:** monitoring stack lives in `observability/docker-compose.yml`, run independently (`docker compose -f observability/docker-compose.yml up -d`). Clean — Promtail ships via Docker socket (sees all containers regardless of network/project), Grafana only talks to Loki internally; zero network coupling with the app stack. Main `docker-compose.yml` only gains `LOG_LEVEL` env lines.
5. **Nginx:** `log_format json_combined escape=json` with ts/method/uri/status/request_time/upstream_response_time/correlation_id → `/dev/stdout`.
6. **Cleanup:** full — replace all `print()` with logger, remove commented-out dead log lines.

Pinned images (same minor for Loki/Promtail): `grafana/loki:3.4.2`, `grafana/promtail:3.4.2`, `grafana/grafana:11.6.0`.

## New files

```
rev-eval/observability/
├── docker-compose.yml                   # STANDALONE monitoring stack: loki + promtail + grafana
│                                        # own project; volumes loki_data, grafana_data defined here
├── loki/loki-config.yml                 # single-binary, filesystem store, TSDB v13 schema,
│                                        # allow_structured_metadata, 168h retention, compactor on
├── promtail/promtail-config.yml         # docker_sd over socket; relabel
│                                        # com_docker_compose_service → service; pipeline:
│                                        # docker stage → json stage (level, correlation_id) →
│                                        # level as LABEL, correlation_id as STRUCTURED METADATA
└── grafana/provisioning/
    ├── datasources/loki.yml             # Loki datasource, default, url http://loki:3100
    └── dashboards/
        ├── dashboards.yml               # file provider pointing at this dir
        └── rev-eval-logs.json           # dashboard (panels below)
```

`observability/docker-compose.yml` contents: `loki` (config mount, `loki_data:/loki`, `-config.file=` command), `promtail` (`/var/run/docker.sock:/var/run/docker.sock:ro` + config mount, `depends_on: loki`), `grafana` (port `3001:3000`, `GF_AUTH_ANONYMOUS_ENABLED=true`, `GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer`, provisioning mount, `grafana_data` volume). Internal default network suffices — no external network join needed. Note: Promtail's docker_sd also captures the monitoring stack's own containers (loki/grafana/promtail logs ship too — harmless, useful for self-debugging).

Per-service new files (4 backend services):
- `services/<svc>/src/utils/logging_config.py` — `JsonFormatter` (fields: ts, level, logger, message, service, correlation_id, exc_info traceback when present), `setup_logging(service_name, level)` (root StreamHandler→stdout; clear `uvicorn`/`uvicorn.error`/`uvicorn.access` handlers + `propagate=True` to avoid double plain-text logs), `correlation_id_ctx: ContextVar` default `"-"`, `get/set_correlation_id()`.
- `services/<svc>/src/middleware/correlation.py` — header-only HTTP middleware (must NOT consume request body — gateway re-reads `await request.body()`): read `X-Correlation-Id`, generate `uuid4().hex` if absent, set contextvar, echo header on response. Gateway and downstream services use the same generate-if-absent logic.

(api-gateway-service already has `src/middleware/`; the other 3 get a new dir.)

## Dashboard panels (`rev-eval-logs.json`) — satisfies criterion 4

1. **Nginx status codes**: `sum by (status) (count_over_time({service="nginx"} | json | __error__="" [5m]))`
2. **Nginx response time p50/p95**: `quantile_over_time(0.95, {service="nginx"} | json | unwrap request_time [5m])` (+0.50 variant; upstream_time series filters `upstream_response_time != ""` — empty on :80 redirects)
3. **Python error counts by service**: `sum by (service) (count_over_time({service=~".+-service|api-gateway"} | json | level=~"ERROR|CRITICAL" [5m]))`
4. **Logs explorer** with `correlation_id` dashboard variable: `{service=~".+"} | json | correlation_id="$correlation_id"`

## Modified files

### `docker-compose.yml` (main — minimal touch)
- Add `LOG_LEVEL: ${LOG_LEVEL:-INFO}` to the 4 backend service env blocks. That's it — monitoring services live in `observability/docker-compose.yml`.
- Do NOT change logging driver — Promtail's `docker` pipeline stage depends on default json-file.

### `.env.example`
- Add `LOG_LEVEL=INFO` under new Observability section.

### `nginx/nginx.conf`
- `http{}`: add `map $http_x_correlation_id $correlation_id { default $http_x_correlation_id; "" $request_id; }` (nginx fallback-generates; gateway is second safety net for BFF/direct traffic that skips nginx), `log_format json_combined escape=json '{...}'`, `access_log /dev/stdout json_combined;`.
- Both `location /api/v1/` (nginx.conf:44) and `location /` (nginx.conf:59): add `proxy_set_header X-Correlation-Id $correlation_id;`.

### `services/api-gateway-service/main.py`
- Lines 14-16: replace `basicConfig` with `setup_logging("api-gateway", getenv("LOG_LEVEL", "INFO"))` (gateway has no settings.py — getenv direct).
- Register correlation middleware near CORS (line ~25).
- httpx call sites — inject `headers["X-Correlation-Id"] = get_correlation_id()` after header cleanup: public auth proxy (line 138), smart route (line 192, after `add_user_context_headers` at 204), legacy route (line 276).
- `traceback.print_exc()` at line 250 → `logger.error(..., exc_info=True)`.
- Legacy route prints at lines 294-295, 309, 312-314 → `logger.info`/`logger.error(..., exc_info=True)`.

### Other 3 services, each:
- `main.py`: call `setup_logging(settings.SERVICE_NAME, settings.LOG_LEVEL)` before `app = FastAPI(...)`; add correlation middleware after CORS.
- `src/config/settings.py`: add `LOG_LEVEL: str = "INFO"` (question-service settings is `case_sensitive=True` — exact uppercase).
- `src/db/session.py`: replace `print()` with module-level `logger` (user-service lines ~41-44; test-mgmt lines ~65-68; question-service ~10 sites incl. `traceback.print_exc()` → `exc_info=True`).

### test-management-service outbound httpx (correlation propagation)
- `src/utils/dependencies.py:39` — the USER_SERVICE_URL call: add `headers={"X-Correlation-Id": get_correlation_id()}`.
- `src/services/test_submission_service.py` — active client calls at lines ~200, 304, 401, 459, 544: add the header. Lines 36/122 are commented out — leave. NOTE: lines ~459/544 reference `settings.INTERVIEW_SERVICE_URL` which doesn't exist (pre-existing latent `AttributeError`) — add header only, do not fix; flag to user.

### test-management-service `src/v1/routes/dashboard_route.py`
- Remove commented-out `# logger.info(...)` dead lines (~52-204); keep live logger at line 13.

### question-management-service
- `main.py` shutdown `print(...)` → `logger.error`. `src/utils/s3_client.py` already uses logger — no change.

### `frontend/src/app/api/v1/[...path]/route.ts`
- Add to fetch headers: `'X-Correlation-Id': request.headers.get('x-correlation-id') ?? crypto.randomUUID()` (browser-origin trace start; BFF path bypasses nginx).

No Dockerfile changes — services `COPY . .` so new src files ship automatically.

## Version control

All work in `rev-eval/` (the git repo) on a new branch:

```bash
git checkout -b richardh-feat-logging richardh   # currently on richardh, clean, synced with origin
```

Matches existing `richardh-feat-*` branch naming (`-feat-pytest`, `-feat-nginx`, `-feat-ruff`, `-feat-uifix`). Commit at each milestone below (Conventional Commits). Push/PR only after user confirms post-verification.

## Implementation order (commit per milestone)

| # | Work | Commit |
|---|---|---|
| 1 | `observability/` tree: standalone docker-compose.yml, loki-config, promtail-config, grafana provisioning + dashboard JSON | `feat(observability): add Loki/Promtail/Grafana monitoring stack` |
| 2 | JSON logging: author `logging_config.py`, copy into 4 services; wire `setup_logging()` in 4 main.py; `LOG_LEVEL` in 3 settings.py + main compose env blocks + `.env.example` | `feat(logging): structured JSON logging across backend services` |
| 3 | print() → logger cleanup: 3 db/session.py, gateway legacy route + traceback.print_exc, question shutdown, dashboard_route dead comment lines | `refactor(logging): replace print calls with logger` |
| 4 | Correlation: `correlation.py` middleware ×4 services, wired in main.py; header on 9 active httpx sites (gateway 3, dependencies.py 1, test_submission_service 5); frontend BFF header | `feat(tracing): propagate X-Correlation-Id across services` |
| 5 | nginx.conf: correlation map + `proxy_set_header` ×2 + `log_format json_combined` + `access_log /dev/stdout` | `feat(nginx): JSON access logs with correlation id` |
| 6 | Verification fixes if any (see below) | fixup or `fix(...)` as needed |

## Verification

1. `docker compose up --build` (app) + `docker compose -f observability/docker-compose.yml up -d` (monitoring) — loki/promtail/grafana healthy; `http://localhost:3001` opens dashboards with no login.
2. `docker compose logs user-service | head` — single-line JSON with `level`/`service`/`correlation_id`; uvicorn access lines also JSON (no plain-text duplicates → proves uvicorn handler fix).
3. Generate traffic: login via frontend + `curl -k https://localhost/api/v1/api/tests` (needs nginx certs present). Note returned `X-Correlation-Id`.
4. Grafana Explore:
   - `{service="nginx"} | json` → status/request_time/correlation_id fields present.
   - `{service=~"api-gateway|user-service"} | json | correlation_id="<id>"` → same id on both hops (end-to-end propagation proven).
   - Error query non-zero after hitting a 404/500 path.
5. Open `rev-eval-logs` dashboard — all 4 panels populated.
6. Trigger an exception → log line carries `exc_info` traceback field, error panel increments.

## Gotchas baked into design

- **Uvicorn double-logging**: `setup_logging` clears uvicorn loggers' handlers + sets propagate — else plain-text AND JSON both ship.
- **Cardinality**: `correlation_id` is structured metadata, NEVER a Loki label (per-request unique → index explosion). Labels: `service`, `container`, `level` only.
- **Loki schema**: TSDB v13 + `allow_structured_metadata: true` required; v11/v12 fails at startup.
- **contextvar default `"-"`**: startup/init_db/seed logs run outside requests — formatter tolerates it.
- **Rootless Docker**: socket path differs (`$XDG_RUNTIME_DIR/docker.sock`) — document in README note; current host is rootful.
- **`start.sh` pre-launch `init_db` bootstrap output** (test-mgmt/question services) runs before main.py import → not JSON. Acceptable; noted.
- **Pre-existing bug flagged, not fixed**: `settings.INTERVIEW_SERVICE_URL` undefined but referenced in `test_submission_service.py:459,544`.
