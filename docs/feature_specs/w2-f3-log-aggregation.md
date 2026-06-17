# W2-F3 — Centralized Log Aggregation and Log Shipping

*Integrate Loki and Grafana to collect and monitor container logs from the reverse proxy and running microservices.*

* **Curriculum Fit**: Day 6 (Centralized logging with Loki/ELK, Docker networks).
* **Prerequisites**: Day 6 topics.
* **Time Estimate**: Without AI tools: 6–10 hours | With AI tools (Gemini/Claude Code): 3–5 hours

## Implementation Details

1. Add Grafana and Loki services to `docker-compose.yml`.
2. Configure the Loki logging driver or mount container standard logs into a Promtail agent container to ship all microservice standard logs to Loki.
3. Establish a standard log formatting utility in Python microservices to print readable JSON logs.
4. Set up a basic Grafana dashboard visualizing Nginx request codes, response times, and Python error trace counts.
