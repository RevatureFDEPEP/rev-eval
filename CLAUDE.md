# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Rev EvalAI** is a Revature AI-powered interview and assessment platform. It uses a microservices architecture with a unified Next.js frontend for conducting and evaluating technical interviews, MCQ tests, and speech-based assessments.

**Key Capabilities:**
- AI-powered interview evaluation and scoring
- Speech-to-speech interview simulations
- MCQ and text-based assessments
- Role-based access (trainers create/score tests, associates take tests)
- Real-time malpractice detection
- Automated transcript generation and summarization

## Architecture

### Monorepo Structure

```
rev-eval-ai/
├── frontend/                    # Next.js 16 application (port 3000)
└── services/                    # Python FastAPI microservices
    ├── api-gateway-service/     # Service routing & discovery (port 8000)
    ├── test-management-service/ # Test & participant CRUD (port 8001)
    ├── question-management-service/
    ├── ai-evaluation-service/   # (Planned)
    ├── notification-service/    # (Planned)
    └── reporting-and-analytics-service/ # (Planned)
```

### Technology Stack

**Frontend:**
- Next.js 16.0.0 (App Router)
- React 19.2.0 with TypeScript 5
- Tailwind CSS 4 + shadcn/ui components
- WorkOS AuthKit for authentication (@workos-inc/authkit-nextjs)
- Package manager: pnpm

**Backend:**
- FastAPI with Uvicorn
- PostgreSQL (SQLAlchemy ORM) + MongoDB
- HashiCorp Consul for service discovery
- Pydantic for validation
- httpx for async HTTP requests

**Planned Integrations:**
- ElevenLabs for voice synthesis
- AWS services (S3, CloudWatch, SNS, SQS)

## Development Commands

### Frontend (from `/frontend`)

```bash
# Install dependencies
pnpm install

# Development server (http://localhost:3000)
pnpm dev

# Production build
pnpm build

# Start production server
pnpm start

# Lint code
pnpm lint

# Add shadcn/ui components
pnpm dlx shadcn@latest add <component-name>
```

**Note on shadcn/ui:** Components install directly to `src/components/ui/` (no nested folder issue). The configuration in `components.json` is already correct with proper aliases.

### Backend Services

#### 1. Start Consul (Required First)

```bash
cd services/api-gateway-service
./consul-setup.sh

# Consul UI: http://localhost:8500
```

#### 2. Start API Gateway

```bash
cd services/api-gateway-service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py

# Health check: http://localhost:8000/health
# Routes list: http://localhost:8000/routes
```

#### 3. Start Test Management Service

```bash
cd services/test-management-service
source venv/bin/activate  # Create venv if needed
pip install -r requirements.txt
python main.py

# API docs: http://localhost:8001/docs
```

#### 4. Start Question Management Service

```bash
cd services/question-management-service
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Development Workflow (Full Stack)

1. **Start infrastructure:**
   ```bash
   # Terminal 1: Start Consul
   cd services/api-gateway-service && ./consul-setup.sh
   ```

2. **Start backend services:**
   ```bash
   # Terminal 2: API Gateway
   cd services/api-gateway-service && python main.py

   # Terminal 3: Test Management
   cd services/test-management-service && python main.py

   # Terminal 4: Question Management (optional)
   cd services/question-management-service && python main.py
   ```

3. **Start frontend:**
   ```bash
   # Terminal 5: Frontend
   cd frontend && pnpm dev
   ```

4. **Verify setup:**
   - Consul UI: http://localhost:8500 (check all services are healthy)
   - API Gateway health: http://localhost:8000/health
   - Frontend: http://localhost:3000
   - API docs: http://localhost:8001/docs

## API Gateway Architecture

### Routing Patterns

The API Gateway supports two routing modes:

#### 1. Smart Routing (Pattern-based) - Preferred
Routes requests based on endpoint patterns without service names in URLs:

```python
ROUTES = [
    {"pattern": r"^/v1/api/tests", "service": "test-management-service"},
    {"pattern": r"^/v1/api/questions", "service": "question-management-service"},
]
```

**Example:**
```bash
# Frontend makes request to gateway
GET http://localhost:8000/v1/api/tests
# → Automatically routed to test-management-service at http://localhost:8001/v1/api/tests
```

#### 2. Legacy Routing (Service name in URL)
```bash
GET http://localhost:8000/test-management-service/v1/api/tests
```

### Service Discovery with Consul

**Registration:**
- Services auto-register with Consul on startup
- TTL-based health checks (15s TTL, 1m deregister timeout)
- Background heartbeat thread (every 10s)
- Auto-deregistration on graceful shutdown

**Discovery:**
- Gateway queries Consul for healthy service instances
- Uses first available healthy instance
- No load balancing (single instance per service currently)

**Failure Handling:**
- 3 consecutive heartbeat failures trigger re-registration attempt
- Failed requests return appropriate HTTP status codes

### Request Forwarding Behavior

**Preserved:**
- Query parameters
- Request body and method
- Most headers (except host, content-length, x-forwarded-*)
- HTTP status codes from downstream services

**Modified:**
- Forces HTTP for internal service communication (not HTTPS)
- Adds 30-second timeout
- Follows redirects automatically

### Current Limitations

**NOT Implemented in API Gateway:**
- ❌ JWT token validation or authentication middleware
- ❌ Authorization/role-based access control
- ❌ Rate limiting or throttling
- ❌ Circuit breaker patterns
- ❌ CORS configuration (handled by individual services)
- ❌ WebSocket support (required for voice interviews)
- ❌ Request/response transformation
- ❌ Caching layer
- ❌ Load balancing across multiple service instances

**Action Items:**
- Add JWT validation middleware to verify WorkOS tokens
- Implement rate limiting using slowapi
- Add CORS middleware for frontend origin
- Upgrade to support WebSocket for real-time voice interviews

## Frontend Architecture

### Directory Structure

```
frontend/src/
├── app/
│   ├── (dashboard)/              # Route group for authenticated routes
│   │   ├── _components/          # Shared dashboard components
│   │   ├── trainer/              # Trainer-specific routes
│   │   │   ├── dashboard/
│   │   │   ├── tests/            # Test creation, management
│   │   │   ├── questions/        # Question bank management
│   │   │   ├── scoring/          # Review and score interviews
│   │   │   └── reports/          # Analytics and reports
│   │   ├── associate/            # Associate (student) routes
│   │   │   ├── dashboard/
│   │   │   ├── tests/            # View assigned tests
│   │   │   │   ├── [id]/
│   │   │   │   └── take/         # Test-taking interfaces
│   │   │   │       ├── mcq/      # MCQ test UI
│   │   │   │       └── interview/ # Voice interview UI
│   │   │   └── results/          # View scores and feedback
│   │   └── dashboard/            # Role-based redirect
│   ├── api/
│   │   └── auth/                 # WorkOS authentication routes
│   │       ├── login/route.ts
│   │       ├── callback/route.ts
│   │       └── logout/route.ts
│   ├── layout.tsx                # Root layout with AuthKitProvider
│   ├── page.tsx                  # Landing page
│   └── globals.css
├── components/
│   └── ui/                       # shadcn/ui components
├── lib/
│   ├── utils.ts
│   ├── session.ts                # Role detection utilities
│   └── workos-org.ts             # WorkOS organization helpers
└── middleware.ts                 # AuthKit + role-based protection
```

### Recommended Structure for New Features

When implementing new features from user stories:

```
src/
├── app/
│   └── (dashboard)/
│       ├── trainer/
│       │   └── [feature]/
│       │       ├── _components/  # Feature-specific components
│       │       ├── page.tsx
│       │       └── layout.tsx    # Optional feature layout
│       └── associate/
│           └── [feature]/
├── components/
│   ├── ui/                       # shadcn components
│   ├── forms/                    # Reusable form components
│   ├── layouts/                  # Layout components
│   └── shared/                   # Cross-feature shared components
├── lib/
│   ├── api/                      # API client layer (recommended)
│   │   ├── client.ts             # Base API client with auth
│   │   ├── test-management.ts
│   │   ├── questions.ts
│   │   └── ai-evaluation.ts
│   └── hooks/                    # Custom React hooks
└── types/                        # TypeScript type definitions
```

## Authentication & Authorization

### WorkOS AuthKit Flow

1. User clicks "Sign In" → redirects to `/auth/login`
2. Login route redirects to WorkOS hosted authentication UI
3. User authenticates (email/password, SSO, or social login)
4. WorkOS redirects to `/callback` with authorization code
5. Callback exchanges code for encrypted session cookie
6. Middleware validates session and redirects based on role

### Role Mapping

```typescript
WorkOS Organization Role  → Application Role → Dashboard Access
─────────────────────────────────────────────────────────────────
org-trainer              → trainer          → /trainer/dashboard
org-participant          → associate        → /associate/dashboard
org-admin                → admin            → Full system access
(no role)                → associate        → /associate/dashboard (default)
```

### Route Protection (middleware.ts)

**Protected Routes:**
```typescript
'/trainer/*'   → Requires: org-trainer, trainer, org-admin, or admin role
'/associate/*' → Requires: org-participant, participant, or member role
'/dashboard'   → All authenticated users (redirects based on role)
```

**Public Routes:**
- `/` - Landing page
- `/auth/login` - Authentication entry point
- `/api/auth/callback` - OAuth callback
- `/unauthorized` - Access denied page

### Role Detection

Located in `src/lib/session.ts`:
```typescript
export async function getRole(): Promise<string> {
  const session = await getSignedInUser();
  if (!session) return 'associate'; // Default

  // Maps WorkOS role to application role
  return session.role || 'associate';
}
```

### Critical Gap: Backend Authentication

**Current State:**
- ✅ Frontend: WorkOS handles authentication and role-based routing
- ❌ Backend: No JWT validation in API Gateway or microservices
- ❌ No token passing from frontend to backend
- ❌ No user context propagation to services

**Required Implementation:**
1. Extract JWT from WorkOS session in frontend
2. Pass JWT in `Authorization: Bearer <token>` header to API Gateway
3. Add JWT validation middleware in API Gateway
4. Propagate user context to downstream services
5. Implement role-based authorization in service endpoints

## Microservices Details

### Test Management Service

**Location:** `services/test-management-service`

**API Endpoints:**
```
POST   /v1/api/tests                              - Create test
GET    /v1/api/tests                              - List all tests
GET    /v1/api/tests/{id}                         - Get test by ID
PUT    /v1/api/tests/{id}                         - Update test
DELETE /v1/api/tests/{id}                         - Delete test
POST   /v1/api/tests/{id}/participants            - Assign participant to test
DELETE /v1/api/tests/{id}/participants/{email}    - Remove participant from test
```

**Data Models (`services/test-management-service/src/models/`):**

```python
# Test model
class Test(Base):
    id: int (PK)
    name: str
    role: str                    # e.g., "Software Developer"
    curriculum: str              # e.g., "Java Full Stack"
    skills: List[str]            # e.g., ["Python", "SQL", "REST APIs"]
    duration: timedelta          # Test time limit
    created_by: str              # Creator email/ID
    active: bool                 # Published status
    created_at: datetime
    updated_at: datetime
    participants: Relationship   # Many-to-many with Participant

# Participant model
class Participant(Base):
    id: int (PK)
    email: str (unique)          # Student email
    tests: Relationship          # Many-to-many with Test
```

**Architecture Pattern:**
```
src/
├── config/
│   └── settings.py              # Pydantic settings from env vars
├── db/
│   ├── init_db.py               # SQLAlchemy Base
│   └── session.py               # Database session management
├── models/                      # SQLAlchemy ORM models
├── schemas/                     # Pydantic request/response schemas
├── repositories/                # Data access layer (CRUD operations)
├── services/                    # Business logic layer
└── v1/routes/                   # FastAPI routers
```

**Database:**
- Development: SQLite (`dev.db`)
- Production: PostgreSQL (configured via `DB_*` env vars)

### Question Management Service

Similar structure to Test Management Service:
- Routes: `/v1/api/questions/*`
- Consul service discovery enabled
- CRUD operations for questions

**Planned Features (from user stories):**
- Question types: MCQ, multiple correct, yes/no, text
- Visibility controls: public, protected, private
- Categorization: topic, module, unit, skill
- Vector database integration (Milvus) for semantic search

### Placeholder Services (Not Yet Implemented)

**AI Evaluation Service:**
- Speech-to-text conversion
- Text-to-speech generation (ElevenLabs)
- Response evaluation using NLP
- Malpractice detection (plagiarism, AI-generated content)
- Transcript summarization with timestamp mapping

**Notification Service:**
- Email notifications (test assignments, results)
- In-app notifications
- SMS notifications (optional)
- Template management
- SQS queue-based processing

**Reporting & Analytics Service:**
- Performance aggregation and metrics
- Outlier detection (25th/75th percentile flagging)
- Dashboard data APIs
- Trend analysis and comparisons

## Feature Implementation Guidance

### Speech-to-Speech Interviews (User Story 5.1)

**Architecture:**
```
Frontend (Audio Recording via WebRTC)
    ↓ WebSocket connection
API Gateway (WebSocket upgrade required)
    ↓
Voice Interview Service (new)
    ↓ Audio → Text
ElevenLabs API / Speech-to-Text
    ↓ Text → AI Response
AI Evaluation Service
    ↓ Response → Audio
ElevenLabs TTS
    ↓ Audio stream
Frontend (Real-time playback)
```

**Required Changes:**
1. **API Gateway:** Add WebSocket support (currently HTTP only)
2. **New Service:** `voice-interview-service` with WebSocket handlers
3. **Frontend:** WebRTC audio capture at `/associate/tests/take/interview`
4. **ElevenLabs Integration:** Text-to-speech and speech-to-text APIs

**Delay Detection (Fail-safe System):**
- Track response timing: 5s warning → 30s warning → 2min pause
- After 3rd warning: pause test, request justification
- Trainer approval/rejection workflow
- Implemented in frontend timer + backend state tracking

### MCQ Test Taking (User Story 5.2)

**Frontend Location:** `/associate/tests/take/mcq/[testId]`

**Components Needed:**
- Question display with multiple choice options
- Navigation (previous/next/review)
- Timer with auto-submit
- Progress indicator
- Answer review before final submission
- Local storage for answer persistence

**API Integration:**
```typescript
// Fetch test questions
GET /v1/api/tests/{testId}/questions

// Submit answers
POST /v1/api/tests/{testId}/submit
{
  "answers": [
    {"questionId": 1, "selectedOptions": [2]},
    {"questionId": 2, "selectedOptions": [1, 3]}  // Multiple correct
  ]
}
```

### Video Upload Support (Planned)

**Required Infrastructure:**
1. S3 bucket for video storage
2. Pre-signed URL generation in backend
3. CloudFront for video streaming
4. Video processing service (optional: transcoding)

**Implementation:**
```
Frontend → Request upload URL → Backend generates pre-signed URL
Frontend → Upload directly to S3 → Notify backend of completion
Backend → Store video metadata → Trigger processing (if needed)
```

### Trainer Scoring Workflow (User Story 2.1)

**Location:** `/trainer/scoring`

**Required Features:**
1. Fetch completed tests with AI scores
2. Display transcript with timestamps
3. Audio/video playback with seek functionality
4. Summary view with links to transcript sections
5. Dual scoring: AI score (read-only) vs Trainer score (editable)
6. Comment/feedback annotation
7. Override and save final score

**API Endpoints Needed:**
```
GET  /v1/api/tests/{testId}/transcript
GET  /v1/api/tests/{testId}/summary
GET  /v1/api/tests/{testId}/recording     # Audio/video URL
POST /v1/api/tests/{testId}/trainer-score
{
  "trainerId": "...",
  "score": 85,
  "comments": "...",
  "overrideAiScore": true
}
```

## Environment Configuration

### Frontend (.env.local)

```bash
# WorkOS Authentication (Required)
WORKOS_API_KEY=sk_live_...                              # From WorkOS dashboard
WORKOS_CLIENT_ID=client_...                             # From WorkOS dashboard
WORKOS_COOKIE_PASSWORD=<random-32-char-string>          # Generate secure random string
NEXT_PUBLIC_WORKOS_REDIRECT_URI=http://localhost:3000/callback
WORKOS_DEFAULT_ORG=org_...                              # Your organization ID

# API Gateway
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Optional
AUTH_MODE=ON                                             # Set to OFF to disable auth
NODE_ENV=development
```

**Generate WORKOS_COOKIE_PASSWORD:**
```bash
openssl rand -base64 32
```

### API Gateway (.env)

```bash
SERVICE_NAME=api-gateway
PORT=8000
SERVICE_HOSTNAME=127.0.0.1

# Consul
CONSUL_HOST=127.0.0.1
CONSUL_PORT=8500
```

### Microservices (.env template)

```bash
# PostgreSQL Database
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=postgres
DB_PASSWORD=your_password
DB_NAME=evalai

# MongoDB (for certain services)
MONGO_USER=admin
MONGODB_PASSWORD=your_password

# Service Configuration
SERVICE_NAME=test-management-service    # Unique per service
PORT=8001                               # Unique per service
SERVICE_HOSTNAME=127.0.0.1

# Consul Service Discovery
CONSUL_HOST=127.0.0.1
CONSUL_PORT=8500

# CORS
ALLOW_ORIGINS=http://localhost:3000,http://localhost:8000
```

**Note:** Each microservice needs its own unique `SERVICE_NAME` and `PORT`.

## Testing

**Current State:** No test suites configured

**Recommended Setup:**

**Backend:**
```bash
# Install pytest
pip install pytest pytest-asyncio httpx

# Run tests
pytest services/test-management-service/tests/
```

**Frontend:**
```bash
# Install testing libraries
pnpm add -D jest @testing-library/react @testing-library/jest-dom

# Run tests
pnpm test
```

## Git Workflow

- **Main Branch:** `main` (production-ready code)
- **Development:** Feature branches → PR to main
- **Recent Work:** Dynamic routing, API gateway, WorkOS authentication setup

## Common Issues & Solutions

### Issue: Consul services not appearing as healthy

**Solution:**
```bash
# Check Consul is running
curl http://localhost:8500/v1/status/leader

# Verify service registered
curl http://localhost:8500/v1/agent/services

# Check service logs for heartbeat errors
# Ensure SERVICE_NAME and PORT env vars are set correctly
```

### Issue: Frontend auth not working

**Solution:**
1. Verify all WorkOS env vars are set in `.env.local`
2. Check `WORKOS_DEFAULT_ORG` matches your organization
3. Ensure `WORKOS_COOKIE_PASSWORD` is 32+ characters
4. Restart Next.js dev server after env changes

### Issue: API Gateway can't find service

**Solution:**
1. Ensure service is registered in Consul (`http://localhost:8500`)
2. Check service is passing health checks
3. Verify route pattern in `api-gateway-service/main.py` matches your endpoint
4. Check API Gateway logs for routing decisions

### Issue: CORS errors from frontend to backend

**Solution:**
1. Add frontend URL to `ALLOW_ORIGINS` in service `.env`
2. Restart the service
3. For API Gateway, CORS middleware not yet implemented (see limitations)

### Issue: shadcn components not found

**Solution:**
```bash
# Verify components.json exists and has correct aliases
cat frontend/components.json

# Reinstall component
cd frontend
pnpm dlx shadcn@latest add button

# Check import path matches alias
import { Button } from "@/components/ui/button"
```

## Port Allocation

| Service                  | Port | URL                              |
|--------------------------|------|----------------------------------|
| Frontend (Next.js)       | 3000 | http://localhost:3000            |
| API Gateway              | 8000 | http://localhost:8000            |
| Test Management Service  | 8001 | http://localhost:8001            |
| Question Management      | 8002 | http://localhost:8002 (typical)  |
| Consul UI                | 8500 | http://localhost:8500            |

## Key Implementation Patterns

### Adding a New Microservice

1. **Create service directory:**
   ```bash
   cd services
   mkdir new-service
   cd new-service
   ```

2. **Initialize structure:**
   ```
   new-service/
   ├── main.py                    # Entry point with Consul registration
   ├── requirements.txt
   ├── .env
   └── src/
       ├── config/settings.py
       ├── db/
       ├── models/
       ├── schemas/
       ├── repositories/
       ├── services/
       └── v1/routes/
   ```

3. **Copy Consul registration from existing service** (e.g., test-management-service/main.py)

4. **Add route to API Gateway:**
   ```python
   # services/api-gateway-service/main.py
   ROUTES = [
       # ... existing routes
       {"pattern": r"^/v1/api/new-feature", "service": "new-service"},
   ]
   ```

5. **Configure .env with unique SERVICE_NAME and PORT**

### Adding a New Frontend Feature

1. **Create route:**
   ```bash
   cd frontend/src/app/(dashboard)/trainer  # or associate
   mkdir feature-name
   ```

2. **Create page component:**
   ```typescript
   // frontend/src/app/(dashboard)/trainer/feature-name/page.tsx
   export default function FeaturePage() {
     return <div>Feature content</div>
   }
   ```

3. **Add navigation:**
   Update dashboard navigation component to include new feature link

4. **Create API client:**
   ```typescript
   // frontend/src/lib/api/feature-name.ts
   export async function getFeatureData() {
     const response = await fetch(
       `${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/api/feature`
     );
     return response.json();
   }
   ```

### Service-to-Service Communication

**Current:** Services are independent, communicate only through API Gateway

**For direct service communication:**
```python
import httpx
from src.config.settings import settings

# Discover service via Consul
async def call_other_service(service_name: str, endpoint: str):
    import consul
    c = consul.Consul(
        host=settings.CONSUL_HOST,
        port=settings.CONSUL_PORT
    )

    # Get healthy service instance
    _, services = c.health.service(service_name, passing=True)
    if not services:
        raise Exception(f"No healthy {service_name} found")

    service = services[0]
    service_url = f"http://{service['Service']['Address']}:{service['Service']['Port']}"

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{service_url}{endpoint}")
        return response.json()
```

## Project Status

### Implemented ✅
- API Gateway with Consul service discovery and pattern-based routing
- Test Management Service (complete CRUD)
- Question Management Service (basic structure)
- Frontend authentication with WorkOS AuthKit
- Role-based dashboards (trainer/associate)
- Next.js App Router with TypeScript
- shadcn/ui component library

### In Progress 🚧
- JWT token integration between frontend and backend
- Additional microservices (AI Evaluation, Notifications, Analytics, User Service)
- MCQ test-taking interface
- Trainer scoring workflow

### Planned 📋
- Speech-to-speech interview feature with ElevenLabs
- Video upload and processing
- Malpractice detection (plagiarism, AI-generated content, delays)
- Transcript summarization with timestamp mapping
- Rate limiting and circuit breakers in API Gateway
- WebSocket support for real-time features
- Comprehensive test suites (pytest, Jest)
- CI/CD pipeline
- Production deployment configuration

## Resources

- **WorkOS Docs:** https://workos.com/docs
- **Next.js App Router:** https://nextjs.org/docs/app
- **shadcn/ui Components:** https://ui.shadcn.com
- **FastAPI:** https://fastapi.tiangolo.com
- **Consul:** https://www.consul.io/docs
- **SQLAlchemy:** https://docs.sqlalchemy.org
- **ElevenLabs API:** https://elevenlabs.io/docs (for voice features)

## Quick Reference

**Most Common Tasks:**

```bash
# Start everything (in separate terminals)
cd services/api-gateway-service && ./consul-setup.sh
cd services/api-gateway-service && python main.py
cd services/test-management-service && python main.py
cd frontend && pnpm dev

# Add new shadcn component
cd frontend && pnpm dlx shadcn@latest add <component>

# View Consul services
open http://localhost:8500

# View API documentation
open http://localhost:8001/docs

# Check service health
curl http://localhost:8000/health

# Test API endpoint
curl http://localhost:8000/v1/api/tests
```
