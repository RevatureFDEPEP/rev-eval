# Rev-Eval Frontend

The Next.js app for Rev-Eval: a trainer interface for creating and reviewing assessments and a participant interface for taking them.

- **Stack:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS, Vitest
- **Package manager:** pnpm 9 (`pnpm-lock.yaml`)

## Roles and routing

`src/middleware.ts` verifies the session JWT (from an httpOnly cookie) with `jose` on every non-public request, then routes by role:

| Path | Allowed roles |
|------|---------------|
| `/trainer/*` (dashboard, tests, questions) | `TRAINER`, `ADMIN` |
| `/participant/*` (dashboard, tests) | `PARTICIPANT` |
| `/dashboard` | redirects to the trainer or participant dashboard by role |

Unauthenticated users are redirected to the sign-in page (`/`), and users without the right role to `/unauthorized`.

## How it reaches the backend

The browser never holds the token in JavaScript. Login (`src/app/api/auth/login`) calls the API gateway and stores the returned JWT in an httpOnly cookie. Requests to `/api/v1/*` go through a server-side proxy route (`src/app/api/v1/[...path]`) that reads the cookie and forwards the call to the gateway with `Authorization: Bearer <token>`. The gateway address comes from `API_GATEWAY_URL`.

## Run locally

The frontend is normally started with the rest of the stack from the repository root:

```bash
cp .env.example .env
docker compose up --build
```

The app is then at http://localhost:3000. To run it on its own against an already running gateway:

```bash
cd frontend
pnpm install
pnpm dev          # needs API_GATEWAY_URL and the same JWT_SECRET the backend uses
```

## Scripts

| Command | What it does |
|---------|--------------|
| `pnpm dev` | development server |
| `pnpm build` | production build |
| `pnpm start` | serve the production build |
| `pnpm lint` | ESLint with zero warnings allowed |
| `pnpm test` | Vitest unit tests |

End-to-end Playwright tests live in [`../e2e/`](../e2e/). See the [root README](../README.md) for the architecture and what CI runs.
