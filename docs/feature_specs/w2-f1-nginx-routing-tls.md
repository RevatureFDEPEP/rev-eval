# W2-F1 — Nginx Path-Based Routing & Local TLS Setup (Reverse Proxy Hookup)

*Trainees wire Nginx to serve as the unified, secure entrance to the platform.*

* **Curriculum Fit**: Day 6 (Nginx Reverse Proxy, Local TLS/SSL, Path-based Routing).
* **Prerequisites**: Day 6 topics.
* **Status**: REQUIRED — Foundational entry point dependency for multiple features across Weeks 3 and 4. Completing this early unlocks the widest range of subsequent work.
* **Required for**: W3-F3 (Test-Taking Frontend Skeleton), W3-F6 (Playwright E2E and Smoke Script), W4-F2 (Candidate Results Page), W4-F4 (Trainer Dashboard)
* **Time Estimate**: Without AI tools: 3–5 hours | With AI tools (Gemini/Claude Code): 1–2 hours

## Implementation Details

1. Modify `nginx/nginx.conf` to act as a reverse proxy on port 80 (and port 443 for TLS).
2. Configure routes: pass `/` and `/_next/*` to the frontend container (port 3000) and `/api/v1/*` to the api-gateway (port 8000).
3. Generate local certificates (using mkcert or openssl) and mount them into Nginx.
4. Update frontend environment variables to access the gateway securely via `/api/v1` instead of cross-port requests, resolving local CORS issues.
