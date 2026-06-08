# W2-F3 — Centralized Log Aggregation & Log Shipping

**Status:** ✅ Completed
**Spec:** `days_6_10_features.md` §3 (Day 6)
**Last updated:** 2026-06-04

Integrate Loki and Grafana to collect and monitor container logs from the
reverse proxy and the microservices. Delivered via PR #38.

## Steps

- [x] **1. Grafana + Loki services** — `observability/` directory with its own
      `docker-compose.yml` (Loki, Promtail, Grafana + provisioned dashboards),
      commit `06d9a4a`.
- [x] **2. Log shipping** — Promtail agent ships container stdout logs to Loki.
- [x] **3. JSON log formatting utility** — structured JSON logging across all
      backend services (commit `6cd3162`); `print` calls replaced with logger
      (commit `332d3ec`).
- [x] **4. Grafana dashboard** — visualizes nginx request codes / response
      times from the `json_combined` access log format and Python error traces.

## Beyond spec

- `X-Correlation-Id` propagated nginx → gateway → downstream services (commit
  `57f0f0a`); shared `correlation_id` key across nginx and Python JSON logs, so
  one request is traceable end-to-end in Grafana.
- Nginx JSON access logs (commit `f4283ff`) — see [W2-F1](w2-f1-nginx-routing-tls.md).

## Remaining

None.
