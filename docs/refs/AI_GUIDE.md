# AI_GUIDE.md - Rules for AI Assistants

> This guide defines rules, invariants, and workflows that AI assistants MUST follow when modifying this repository.

**SAFETY GUARD:** Commands, workflows, and code snippets in this document are reference-only. Do not run, deploy, edit, or commit unless explicitly requested and approved by the user.

---

## 1. PROJECT OVERVIEW

**Name:** Reframing Retirement Coach
**Purpose:** Autonomy-supportive AI coaching application helping newly retired adults adopt and maintain physical activity
**Domain:** Health behavior change (non-clinical)
**Framework:** M-PAC (Multi-Process Action Control) + Motivational Interviewing

---

## 2. TECH STACK

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.11), Uvicorn |
| LLM | OpenAI GPT-4o |
| Embeddings | OpenAI text-embedding-3-large (3072 dim) |
| Vector DB | Qdrant v1.16.3 |
| STT | OpenAI Whisper |
| TTS | OpenAI TTS (voice: "nova") |
| Frontend | Vanilla HTML5/CSS3/JavaScript (NO frameworks) |
| Auth | X-API-Key header |
| Rate Limiting | slowapi |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions → AWS Lightsail |

---

## 3. DIRECTORY STRUCTURE

```
/
├── backend/              # FastAPI application
│   ├── app.py           # Main app, routes, static serving
│   ├── models.py        # Pydantic request/response schemas
│   ├── session_store.py # In-memory session management
│   ├── middleware/      # Auth and rate limiting
│   └── voice/           # STT/TTS routes
├── coach/               # Core coaching agent
│   └── agent.py         # CoachAgent class (state, prompting, streaming)
├── prompts/             # System prompt templates
│   └── prompt.py        # Main coach system prompt
├── rag/                 # Retrieval-Augmented Generation
│   ├── config.py        # RAG configuration
│   ├── router.py        # Query routing (master vs activities)
│   ├── retriever.py     # Qdrant retrieval
│   └── ingest.py        # Data ingestion
├── frontend/            # Static web UI
│   ├── index.html       # Production HTML
│   ├── app.js           # Main JS logic
│   └── styles.css       # All styling
├── Data/                # Knowledge base files
├── tests/               # Python unit tests
├── docker-compose.yml   # Multi-container orchestration
├── Dockerfile           # Multi-stage build
└── .env.example         # Configuration template
```

---

## 4. CRITICAL FILES (Handle with Care)

| File | Reason |
|------|--------|
| `prompts/prompt.py` | Core coaching personality and safety boundaries |
| `coach/agent.py` | M-PAC layer detection, response routing, state management |
| `backend/middleware/auth.py` | Security - API key validation |
| `backend/middleware/rate_limit.py` | Abuse prevention |
| `.env` | Contains secrets - NEVER commit |
| `docker-compose.yml` | Production service configuration |
| `.github/workflows/deploy.yml` | CI/CD pipeline |

---

## 5. DOMAIN CONSTRAINTS (STRICT)

### 5.1 The Coach MUST NOT:
- Diagnose medical or mental health conditions
- Interpret symptoms, injuries, or clinical test results
- Provide medical advice, treatment plans, or exercise clearance
- Recommend medications, supplements, or dosages
- Handle emergencies (must redirect to professional help)
- Provide legal, financial, or insurance advice
- Claim to be a clinician or medical expert

### 5.2 Out-of-Scope Handling
If user asks off-topic questions, enforce 3-step boundary:
1. "I can't help with that."
2. "What I can help with is [coaching scope]."
3. Ask one grounded question about physical activity

### 5.3 M-PAC Framework (NEVER Expose to Users)
The coach silently tracks behavioral layers:
- **Reflexive:** Automatic habits
- **Regulatory:** Planning/execution
- **Ongoing Reflective:** Enjoyment/meaning
- **Initiating Reflective:** Deciding to start

These are internal state variables - NEVER mention "layer", "stage", or "M-PAC" to users.

The M-PAC framework is used solely to inform internal state tracking and response selection logic and is never used to label, score, or categorize users.

### 5.4 Response Mode Routing
| User State | Response Style |
|------------|----------------|
| Unmotivated ("why bother") | Education only, no questions, no action suggestions |
| Negative emotions | Supportive education, no pressure |
| Explicit knowledge request | Info-focused, may cite modules |
| Default | Full coaching with questions and planning |

---

## 6. CODING CONVENTIONS

### 6.1 Python
- Use Pydantic for all request/response validation
- Async/await for all I/O operations
- Type hints required
- Environment variables via `os.getenv()` with defaults
- Middleware as decorators (`@require_api_key`)

### 6.2 Frontend JavaScript
- Vanilla JS only - NO frameworks (React, Vue, etc.)
- Use native Web APIs (MediaRecorder, Web Audio, SSE)
- Store API key in `sessionStorage` (not localStorage)
- Block input during bot response (`isProcessing` flag)

### 6.3 CSS
- CSS custom properties for theming (`--color-primary`)
- Mobile-first responsive design
- Accessibility: ARIA labels, focus states, `.sr-only`

### 6.4 Commits
- Imperative mood: "Add feature" not "Added feature"
- Never commit `.env` or secrets

---

## 7. SECURITY INVARIANTS

### 7.1 Authentication
- All endpoints (except `/healthz`) require `X-API-Key` header
- Constant-time comparison (`secrets.compare_digest`)
- API keys from `API_KEYS` env var (comma-separated)

### 7.2 Rate Limiting
- Per API key (not IP-based)
- Messages: 100/hour
- Session creation: 20/hour
- Max 50 sessions per API key, 1000 global

### 7.3 Input Validation
- Max message length: 10,000 chars
- Max audio file: 10 MB
- Max history: 100 messages per session
- Detect excessive character repetition (>80%)

### 7.4 Prompt Injection
- Detection patterns in `coach/agent.py`
- Logged but not blocked (system prompt resists)
- RAG content sanitized before injection

---

## 8. DEVELOPMENT COMMANDS

### Local Development
```bash
# Start all services
docker-compose up

# With hot-reload (if override exists)
docker-compose -f docker-compose.yml -f docker-compose.override.yml up

# Rebuild after code changes
docker-compose build --no-cache && docker-compose up
```

### Testing
```bash
# Run unit tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_rag_routing.py -v
```

### Deployment
Automatic on push to `main` via GitHub Actions:
1. SSH to Lightsail
2. `git pull`
3. `docker-compose down`
4. `docker-compose build --no-cache`
5. `docker-compose up -d`

---

## 9. ENVIRONMENT VARIABLES

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API credentials |
| `API_KEYS` | Yes | Auth tokens (comma-separated) |
| `ALLOWED_ORIGINS` | Yes | CORS whitelist |
| `QDRANT_URL` | Yes | Vector DB endpoint |
| `QDRANT_API_KEY` | No | Qdrant auth (optional) |
| `SESSION_TTL_MINUTES` | No | Session expiration (default: 90) |
| `MAX_MESSAGE_LENGTH` | No | Input limit (default: 10000) |
| `LOG_LEVEL` | No | Logging verbosity (default: INFO) |

---

## 10. RAG SYSTEM

### Collections
- `rr_master`: Lesson content from Reframing Retirement curriculum
- `rr_activities`: Local Victoria-area activity resources

### Routing Logic (rag/router.py)
- Activity keywords → query activities collection
- Location hints → filter by area
- Day patterns → filter by schedule
- Default → query master collection

### Content Sanitization
All retrieved content is sanitized:
- Control characters removed
- HTML entities escaped
- Truncated to 1200 chars max
- Prevents injection via retrieved content

---

## 11. SESSION MANAGEMENT

- In-memory storage with TTL (90 min default)
- Random UUID session IDs
- Per-API-key session limits
- Automatic cleanup of expired sessions
- State tracked: `process_layer`, `barrier`, `activities`, `time_available`

---

## 12. CHECKLIST BEFORE MODIFYING

- [ ] Read relevant files before making changes
- [ ] Understand M-PAC framework if touching coach logic
- [ ] Preserve safety boundaries in prompts
- [ ] Never expose internal state variables to users
- [ ] Test with Docker build before pushing
- [ ] Check rate limiting still works after middleware changes
- [ ] Verify CORS configuration for new origins

---

## 13. RESEARCH-PHASE LIMITATIONS (KNOWN & INTENTIONAL)

### 13.1 Frontend End-to-End (E2E) Testing

A frontend end-to-end (E2E) testing suite is not implemented in this repository. This is an intentional research-phase scope decision. System reliability is currently supported through backend unit tests, manual acceptance testing, and Docker-based integration checks during deployment.

---

### 13.2 Session Persistence & Backup / Recovery

Session state is maintained in-memory only and is lost on application restart. This is a deliberate privacy-first design choice intended to minimize persistence of personal data. The system is not a record-keeping or longitudinal tracking tool, and users should not assume long-term storage or recoverability of session history.

---

### 13.3 Multi-Instance / Horizontal Scaling

Horizontal scaling and multi-instance deployments are not supported in the documented architecture. The system is designed for single-instance operation to preserve simplicity of state handling, auditability, and controlled behavior during research-phase deployment.

---

### 13.4 Monitoring, APM, and Error Tracking

No external application performance monitoring (APM) or error-tracking integrations are used. Operational visibility is currently provided through application logs and container health checks. This level of monitoring is considered sufficient for the current deployment scale and non-clinical research context.

---

These limitations reflect the system's current role as a research-phase, non-clinical prototype. Design priorities emphasize privacy minimization, auditability, and controlled deployment scope. Production-scale or clinical-grade use would require revisiting these areas with updated documentation, safeguards, and infrastructure.
