# Rev Eval Project Continuity Review

This review highlights container purpose, project continuity issues, references to services that are not currently wired, and suggested improvements.

## Containers

```text
+-----------------------------+---------+---------------------------------------------+-------------------------------+
| Container                   | Needed? | Purpose                                     | Comment                       |
+-----------------------------+---------+---------------------------------------------+-------------------------------+
| postgres                    | Yes     | DB for users, tests, skills, submissions    | Core current dependency       |
| mongo                       | Yes     | DB for question-management-service          | Required for questions        |
| minio                       | Partial | Local S3-compatible storage for images      | Configured, lightly wired     |
| user-service                | Yes     | Auth, JWT, users                            | Core login service            |
| test-management-service     | Yes     | Tests, skills, submissions                  | Core evaluation service       |
| question-management-service | Yes     | Question bank                               | Used by /questions            |
| api-gateway                 | Yes     | JWT verification and service routing        | Main backend entrypoint       |
| frontend                    | Yes     | Next.js UI                                  | Main application              |
| nginx                       | Not now | Future reverse proxy                        | Currently returns 502         |
+-----------------------------+---------+---------------------------------------------+-------------------------------+
```

## Inconsistencies

```text
+----+------+----------------------------------------------------------------------------------------------+
| 1  | Line | /Users/alexiscanon/Documents/2026_US/REVATURE/rev-eval/start.sh:96                           |
|    | Note | Checks Consul, but Consul is not defined in docker-compose.yml.                               |
|    | Fix  | Remove this check, or add Consul formally to compose if it is still required.                 |
+----+------+----------------------------------------------------------------------------------------------+
| 2  | Line | /Users/alexiscanon/Documents/2026_US/REVATURE/rev-eval/start.sh:98                           |
|    | Note | Checks notification-service on port 8004, but that service was removed.                       |
|    | Fix  | Remove this healthcheck; user_service.py already says notification-service was removed.       |
+----+------+----------------------------------------------------------------------------------------------+
| 3  | Line | /Users/alexiscanon/Documents/2026_US/REVATURE/rev-eval/start.sh:101                          |
|    | Note | Checks AI Quiz Service on port 8005, but there is no container or gateway route for it.       |
|    | Fix  | Remove it from the script, or implement the real service and register /v1/api/test-sessions.  |
+----+------+----------------------------------------------------------------------------------------------+
| 4  | Line | /Users/alexiscanon/Documents/2026_US/REVATURE/rev-eval/frontend/src/lib/api/quiz-sessions.ts:27 |
|    | Note | UI calls /v1/api/test-sessions, but the gateway only routes auth/users/dashboard/tests/       |
|    |      | submissions/skills/questions.                                                                |
|    | Fix  | Create a test-session service/router, or disable the adaptive MCQ flow until it exists.       |
+----+------+----------------------------------------------------------------------------------------------+
| 5  | Line | /Users/alexiscanon/Documents/2026_US/REVATURE/rev-eval/services/api-gateway-service/main.py:43 |
|    | Note | ROUTES does not include /v1/api/test-sessions, even though the frontend uses it.              |
|    | Fix  | Add a registry entry only once the backend exists; this is a good seam for the change.        |
+----+------+----------------------------------------------------------------------------------------------+
| 6  | Line | /Users/alexiscanon/Documents/2026_US/REVATURE/rev-eval/services/test-management-service/main.py:33 |
|    | Note | dashboard_route is not registered, but the gateway/API routes call /dashboard/trainer/*.      |
|    | Fix  | Remove dead dashboard routes or reactivate dashboard_route with correct async queries.        |
+----+------+----------------------------------------------------------------------------------------------+
| 7  | Line | /Users/alexiscanon/Documents/2026_US/REVATURE/rev-eval/services/test-management-service/src/v1/routes/dashboard_route.py:45 |
|    | Note | Dashboard endpoints are commented out.                                                       |
|    | Fix  | Delete the file if frontend aggregation replaced it, or reimplement and register it.          |
+----+------+----------------------------------------------------------------------------------------------+
| 8  | Line | /Users/alexiscanon/Documents/2026_US/REVATURE/rev-eval/nginx/nginx.conf:12                   |
|    | Note | Nginx always returns 502; it is not part of the functional app today.                         |
|    | Fix  | Remove it from compose for dev, or complete proxy routing to frontend/api-gateway.            |
+----+------+----------------------------------------------------------------------------------------------+
| 9  | Line | /Users/alexiscanon/Documents/2026_US/REVATURE/rev-eval/.github/workflows/ci-pipeline.yml:42  |
|    | Note | CI installs from services/<service>/src, but requirements.txt is one level above.             |
|    | Fix  | Change working-directory to services/${{ matrix.service }}.                                  |
+----+------+----------------------------------------------------------------------------------------------+
| 10 | Line | /Users/alexiscanon/Documents/2026_US/REVATURE/rev-eval/frontend/pnpm-lock.yaml:11            |
|    | Note | Lockfile keeps dependencies no longer in package.json and is missing jose.                    |
|    | Fix  | Regenerate the lockfile with pnpm 9.15.0 and commit package + lock in sync.                  |
+----+------+----------------------------------------------------------------------------------------------+
| 11 | Line | /Users/alexiscanon/Documents/2026_US/REVATURE/rev-eval/.github/workflows/ci-pipeline.yml:68  |
|    | Note | CI installs pnpm 8, but package.json declares pnpm@9.15.0.                                   |
|    | Fix  | Use pnpm 9.15.0 in CI.                                                                        |
+----+------+----------------------------------------------------------------------------------------------+
| 12 | Line | /Users/alexiscanon/Documents/2026_US/REVATURE/rev-eval/services/api-gateway-service/main.py:257 |
|    | Note | legacy_gateway is declared after catch-all /{path:path}; it is probably unreachable.          |
|    | Fix  | Remove the legacy route, or move it before the catch-all and define consistent auth behavior. |
+----+------+----------------------------------------------------------------------------------------------+
```

## Bottom Line

Not all containers are needed today. `nginx` is optional and incomplete. `minio` is prepared for question images, but the upload endpoint is not wired yet. The biggest continuity issue is deciding whether `test-sessions` / AI Quiz is coming back as a real service or should be temporarily removed from the frontend.
