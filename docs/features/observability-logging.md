# Centralized Log Aggregation and Log Shipping

## Decision Summary

Implemented the Grafana Alloy option for centralized log shipping into Loki, with Grafana provisioned as the query and dashboard surface.

Reasoning:

- Alloy is Grafana's current collector path and supports Docker log collection without requiring every developer to install a host-level Loki Docker logging plugin.
- The setup stays self-contained in `docker-compose.yml`, which fits the Day 6 Docker networks and centralized logging curriculum.
- Docker metadata from `discovery.docker` gives Loki useful low-cardinality labels such as `service`, `container`, `job`, and `environment`.
- Structured JSON logs from Nginx and Python services make LogQL dashboard queries stable and readable.
- Promtail was not chosen because it is deprecated and in long-term support before end-of-life. It can still be discussed as legacy curriculum context, but it is not the best new implementation path.

## Decision Options Defended

| Option | Pros | Cons | Decision |
| --- | --- | --- | --- |
| Grafana Alloy collector | Compose-managed, current Grafana collector, uses Docker metadata, no host logging plugin required. | Requires Docker socket mount and Alloy config. | Implemented. Best fit for this repo and training environment. |
| Loki Docker logging driver | Simple once installed; containers can ship directly to Loki. | Requires a Docker plugin on every workstation; less portable for students and CI; driver behavior affects Docker logging. | Not selected. Keep as fallback only. |
| Promtail | Familiar in older Loki tutorials and some Day 6 examples. | Deprecated; new work would teach a legacy path. | Not selected. Mention only as legacy context. |

## Implementation Details

1. Added Loki, Grafana, and Alloy services to `docker-compose.yml`.
2. Mounted `observability/loki/loki-config.yml` into Loki and persisted data with `loki_data`.
3. Mounted Grafana provisioning directories so the Loki data source and dashboard load automatically.
4. Mounted Docker socket read-only into Alloy so `discovery.docker` and `loki.source.docker` can collect container stdout/stderr logs.
5. Added Nginx JSON access logging with request status, request timing, upstream timing, request ID, method, URI, user agent, and referer.
6. Forwarded `X-Request-ID` from Nginx to downstream services for request correlation.
7. Added JSON logging helpers to each Python service because each microservice has an isolated Docker build context.
8. Installed request logging middleware in each FastAPI app to emit JSON request completion/failure records.
9. Replaced API gateway bare `print`/`traceback.print_exc()` error paths with structured logger calls.
10. Added a Grafana dashboard for Nginx status codes, Nginx p95 request time, Python error counts, and recent Python errors.

## Files Changed or Added

| Path | Action | Purpose |
| --- | --- | --- |
| `docker-compose.yml` | Updated | Adds `loki`, `grafana`, and `alloy` services plus named volumes. |
| `nginx/nginx.conf` | Updated | Adds JSON access logs and forwards `X-Request-ID`. |
| `observability/loki/loki-config.yml` | Added | Loki single-binary local dev config with filesystem storage and retention. |
| `observability/alloy/config.alloy` | Added | Discovers Docker containers, relabels Compose metadata, and writes logs to Loki. |
| `observability/grafana/provisioning/datasources/loki.yml` | Added | Provisions Loki as Grafana's default data source. |
| `observability/grafana/provisioning/dashboards/rev-eval.yml` | Added | Provisions the Rev Eval dashboard folder/provider. |
| `observability/grafana/dashboards/rev-eval-logs.json` | Added | Grafana dashboard for logs and errors. |
| `services/api-gateway-service/src/logging_config.py` | Added | JSON logging formatter and request middleware helper. |
| `services/user-service/src/logging_config.py` | Added | JSON logging formatter and request middleware helper. |
| `services/test-management-service/src/logging_config.py` | Added | JSON logging formatter and request middleware helper. |
| `services/question-management-service/src/logging_config.py` | Added | JSON logging formatter and request middleware helper. |
| `services/api-gateway-service/main.py` | Updated | Initializes JSON logging and request logging; replaces print tracebacks. |
| `services/user-service/main.py` | Updated | Initializes JSON logging and request logging. |
| `services/test-management-service/main.py` | Updated | Initializes JSON logging and request logging. |
| `services/question-management-service/main.py` | Updated | Initializes JSON logging and request logging. |
| `docs/features/observability-logging.md` | Added | Documents decision, implementation, testing, commit steps, and PR message. |

## How to Run

Start only observability services:

```bash
docker compose up -d loki grafana alloy
```

Start the full stack:

```bash
docker compose up -d
```

Open Grafana:

```text
http://localhost:3001
```

Default local credentials:

```text
username: admin
password: admin
```

Useful checks:

```bash
curl -fsS http://localhost:3100/ready
curl -fsS http://localhost:3001/api/health
curl -fsS "http://localhost:3100/loki/api/v1/label/service/values"
```

## Dashboard Queries

Nginx request rate by status:

```logql
sum by (status) (rate({service="nginx"} | json | status=~"[0-9]+" | __error__="" [5m]))
```

Nginx p95 request time:

```logql
quantile_over_time(0.95, {service="nginx"} | json | unwrap request_time | __error__="" [5m])
```

Python error trace count:

```logql
sum by (service) (count_over_time({service=~"api-gateway|user-service|test-management-service|question-management-service"} | json | level=~"ERROR|CRITICAL" | __error__="" [5m]))
```

Recent Python errors:

```logql
{service=~"api-gateway|user-service|test-management-service|question-management-service"} | json | level=~"ERROR|CRITICAL"
```

## Testing Performed

Passed:

```bash
docker compose config
docker run --rm -v "$PWD/observability/alloy/config.alloy:/etc/alloy/config.alloy:ro" grafana/alloy:v1.9.1 validate /etc/alloy/config.alloy
/mnt/c/Users/jorge/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -m json.tool observability/grafana/dashboards/rev-eval-logs.json
/mnt/c/Users/jorge/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -m py_compile services/api-gateway-service/main.py services/api-gateway-service/src/logging_config.py services/user-service/main.py services/user-service/src/logging_config.py services/test-management-service/main.py services/test-management-service/src/logging_config.py services/question-management-service/main.py services/question-management-service/src/logging_config.py
```

Nginx config passed after validating inside a temporary Docker network with the same aliases used by Compose:

```bash
docker network create rev-eval-nginx-test
docker run -d --rm --name rev-eval-test-frontend --network rev-eval-nginx-test --network-alias frontend nginx:alpine sh -c "sleep 120"
docker run -d --rm --name rev-eval-test-api-gateway --network rev-eval-nginx-test --network-alias api-gateway nginx:alpine sh -c "sleep 120"
docker run --rm --network rev-eval-nginx-test -v "$PWD/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" -v "$PWD/nginx/certs:/etc/nginx/certs:ro" nginx:alpine nginx -t
docker rm -f rev-eval-test-frontend rev-eval-test-api-gateway
docker network rm rev-eval-nginx-test
```

Live smoke test passed:

```bash
docker compose up -d loki grafana alloy
docker compose ps loki grafana alloy
curl -fsS http://localhost:3100/ready
curl -fsS http://localhost:3001/api/health
curl -fsS "http://localhost:3100/loki/api/v1/labels"
curl -fsS "http://localhost:3100/loki/api/v1/label/service/values"
docker compose down
docker volume rm rev-eval_loki_data rev-eval_grafana_data rev-eval_alloy_data
```

Observed live smoke result:

- Loki returned `ready`.
- Grafana returned database status `ok`.
- Alloy stayed running with no startup errors.
- Loki label query returned log labels including `container`, `environment`, `job`, `service`, `service_name`, and `source`.
- Loki service values included `alloy`, `grafana`, and `loki`, confirming logs were shipped.

## Failed Testing, Reasons, and Fixes

| Failed check | Reason | Fix |
| --- | --- | --- |
| `python -m json.tool ...` and `python -m py_compile ...` | `python` is not on PATH in this Git Bash/WSL terminal. | Used the bundled Python executable at `/mnt/c/Users/jorge/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`. |
| First bundled Python retry with `/c/Users/...` | This Git Bash uses WSL-style mounts under `/mnt/c`, not Git-for-Windows `/c`. | Switched to `/mnt/c/.../python.exe`. |
| Standalone `nginx -t` in a plain container | Nginx resolves `frontend` and `api-gateway` upstream names at config-test time; those names only exist on the Compose network. | Re-ran `nginx -t` inside a temporary Docker network with `frontend` and `api-gateway` aliases. |
| First temporary-network test command | Shell variable quoting produced an empty Docker network name. | Re-ran the validation with literal network/container names. |

## Not Run

Full end-to-end application validation with all backend databases and frontend services was not run. The scoped smoke test validated the observability stack, config syntax, Python syntax, Grafana health, Loki readiness, and log ingestion from the observability containers. A full app run should be done before merging if the PR gate requires complete service startup.
