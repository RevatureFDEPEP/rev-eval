# W2-F3 — Centralized Log Aggregation & Log Shipping

**Status:** ❌ Not Started
**Spec:** `days_6_10_features.md` §3 (Day 6)
**Last updated:** 2026-06-12

Integrate Loki and Grafana to collect and monitor container logs from the
reverse proxy and the microservices.

## Steps

- [ ] **1. Grafana + Loki services** — `observability/` directory with its own
      `docker-compose.yml` (Loki, Promtail, Grafana + provisioned dashboards).
- [ ] **2. Log shipping** — Promtail agent ships container stdout logs to Loki.
- [ ] **3. JSON log formatting** — structured JSON logging across all backend
      services; `print` calls replaced with logger.
- [ ] **4. Grafana dashboard** — visualizes nginx request codes / response
      times from nginx `json_combined` access log format and Python error traces.

## Evidence

None on `tianyac` branch. `observability/` directory does not exist.

Note: another contributor delivered this feature on a separate branch (PR #38);
that work is not yet merged into `tianyac`.

## Remaining

All steps. Depends on nginx JSON access logs (`log_format json_combined`) added
in [W2-F1](w2-f1-nginx-routing-tls.md) step remaining.
