# jobs.ottobon.cloud — Complete Backend Documentation

> **Version:** 1.0.0  
> **Last Updated:** 2026-03-20  
> **Stack:** FastAPI · Supabase (PostgreSQL + pgvector + Storage + Auth) · OpenAI (GPT-4o-mini / GPT-4o) · Python 3.12 · Crawl4AI · APScheduler · Instructor · feedparser  
> **Production Port:** 8200 (Docker) · 8000 (local dev)

---

## Table of Contents

1.  [Project Overview](#1-project-overview)
2.  [Architecture & SOLID Principles](#2-architecture--solid-principles)
3.  [Directory Structure](#3-directory-structure)
4.  [Configuration & Environment Variables](#4-configuration--environment-variables)
5.  [Database Schema](#5-database-schema)
6.  [Dependency Injection System](#6-dependency-injection-system)
7.  [Authentication Flow](#7-authentication-flow)
8.  [API Endpoints — Complete Reference](#8-api-endpoints--complete-reference)
9.  [Core Pipelines — Detailed Breakdown](#9-core-pipelines--detailed-breakdown)
10. [AI Enrichment Pipeline](#10-ai-enrichment-pipeline)
11. [Resume Processing Pipeline](#11-resume-processing-pipeline)
12. [Matching Engine & Skill Gap Analysis](#12-matching-engine--skill-gap-analysis)
13. [Resume Tailoring (AI Rewrite)](#13-resume-tailoring-ai-rewrite)
14. [Job Ingestion & Scheduling](#14-job-ingestion--scheduling)
15. [Web Scraper System](#15-web-scraper-system)
16. [Control Tower — WebSocket Chat System](#16-control-tower--websocket-chat-system)
17. [Mock Interview System](#17-mock-interview-system)
18. [Blog Generation Agent](#18-blog-generation-agent)
19. [Market News Service (RSS)](#19-market-news-service-rss)
20. [Analytics & Market Intelligence](#20-analytics--market-intelligence)
21. [Admin Dashboard API](#21-admin-dashboard-api)
22. [Deployment](#22-deployment)
23. [Setup & Run Instructions](#23-setup--run-instructions)
24. [Dependencies](#24-dependencies)
25. [Database Migrations](#25-database-migrations)
26. [Production Hardening Notes](#26-production-hardening-notes)

---

## 1. Project Overview

**jobs.ottobon.cloud** is an **Outcome-Driven Recruitment Ecosystem** that connects job providers directly with job seekers. Unlike traditional job boards, every job listing is automatically enriched with AI-generated career coaching content.

### Business Model: Hybrid Sourcing

| Channel | Description |
|---|---|
| **Direct Posting** | Providers post jobs via the API. AI enrichment triggers automatically. |
| **Automated Ingestion** | A daily scheduler scrapes entry-level roles (0–2 years) from Big 4 firms (Deloitte, PwC, KPMG, EY). |

### Core Value Propositions

| Feature | Description |
|---|---|
| **4-Pillar AI Enrichment** | Every job automatically receives: 5 resume optimization bullets, 5 interview questions with answer strategies, extracted skills list, and estimated salary range. |
| **AI Career Coach (Chat)** | Real-time WebSocket chat with a personalized AI mentor that knows the user's resume and the job they're exploring. |
| **Semantic Matching** | Vector-based cosine similarity (pgvector) between user resumes and job descriptions. Scores below 0.7 trigger AI gap analysis + missing skills extraction + learning recommendations. |
| **Mock Interview System** | Structured mock interviews using the job's AI-generated prep questions, auto-scored by AI on technical accuracy, clarity, and confidence. |
| **Resume Tailoring** | AI rewrites the user's resume to specifically target a job description using ATS-optimized keywords. |
| **Blog Generation** | AI agent generates weekly career strategy posts for students using real-time Google News RSS data about Big 4 hiring trends. |
| **Market Intelligence** | Aggregated analytics dashboard: top skills, salary trends, company distribution, work styles, experience levels. |

### User Roles

| Role | Capabilities |
|---|---|
| `seeker` | Upload resume (PDF/DOCX), browse jobs, check match scores, get gap analysis, tailor resume to a job, chat with AI coach, take mock interviews, download resume |
| `provider` | Post jobs (triggers AI enrichment), view own listings, trigger manual ingestion |
| `admin` | Intercept chat sessions, send messages to seekers, trigger ingestion, re-enrich jobs, generate blog posts, view all sessions, trigger scraping |

---

## 2. Architecture & SOLID Principles

The backend follows a **Ports & Adapters (Hexagonal) Architecture** with strict SOLID enforcement:

```
┌──────────────────────────────────────────────────────────────┐
│                    ROUTERS (HTTP / WebSocket)                 │
│   Thin layer — parse request → call service → respond        │
│   auth.py · users.py · jobs.py · matching.py · chat.py       │
│   admin.py · ingestion.py · blog.py · analytics.py           │
│   mock_interviews.py                                         │
└────────────────────────────┬─────────────────────────────────┘
                             │ calls
┌────────────────────────────▼─────────────────────────────────┐
│                   SERVICES (Business Logic)                   │
│   Orchestrates workflows, depends on PORTS only              │
│   auth_service · user_service · job_service                  │
│   enrichment_service · matching_service · chat_service        │
│   ingestion_service · analytics_service                      │
│   mock_interview_service · market_news_service               │
└────────────────────────────┬─────────────────────────────────┘
                             │ depends on
┌────────────────────────────▼─────────────────────────────────┐
│                PORTS (Abstract Interfaces — ABCs)             │
│   AIPort · EmbeddingPort · DatabasePort · DocumentPort        │
│   StoragePort · ScraperPort · UserPort · JobPort              │
│   BlogPort · ChatPort · MockInterviewPort · PdfPort           │
└────────────────────────────┬─────────────────────────────────┘
                             │ implemented by
┌────────────────────────────▼─────────────────────────────────┐
│               ADAPTERS (Concrete Implementations)             │
│   OpenAIAdapter · OpenAIEmbeddingAdapter · SupabaseAdapter    │
│   SupabaseStorageAdapter · DocumentAdapter · PyPdfAdapter     │
│   DeloitteAdapter · PwCAdapter · KPMGAdapter · EYAdapter      │
└──────────────────────────────────────────────────────────────┘
```

### SOLID Mapping

| Principle | Implementation |
|---|---|
| **S — Single Responsibility** | Each file/class has one concern. Routers contain zero business logic. Services handle orchestration. Adapters handle external I/O. |
| **O — Open/Closed** | To add a new AI provider (e.g., Anthropic), create a new adapter implementing `AIPort`. Nothing else changes. |
| **L — Liskov Substitution** | Any `AIPort` implementation can replace `OpenAIAdapter` without breaking the system. Same for all ports. |
| **I — Interface Segregation** | `DatabasePort` aggregates five focused sub-ports: `UserPort`, `JobPort`, `BlogPort`, `ChatPort`, `MockInterviewPort`. Each has 2–6 methods. |
| **D — Dependency Inversion** | Services declare dependencies on abstract `Port` types. `dependencies.py` wires concrete adapters at startup. |

---

## 3. Directory Structure

```
backend/
├── .env                            # Environment variables (SECRET)
├── .gitignore
├── .dockerignore
├── Dockerfile                      # Python 3.12-slim + Playwright + Chromium
├── docker-compose.yml              # Single-service compose (port 8200)
├── requirements.txt                # 15 Python dependencies
├── main.py                         # FastAPI entry point + lifespan events
├── docs/                           # Documentation
│   └── BACKEND_DOCUMENTATION.md    # This file
│
├── migrations/                     # SQL migration files
│   ├── 003_cron_locks.sql
│   ├── 004_blog_posts.sql
│   ├── 004_hnsw_index.sql
│   ├── 005_add_archived_at.sql
│   ├── 005_rls_policies.sql
│   ├── 006_learning_resources.sql
│   ├── 006_setup_blog_and_seed.sql
│   ├── 007_mock_interviews.sql
│   ├── add_password_column.sql
│   ├── data_migration_to_org.sql
│   └── org_schema_setup.sql
│
├── scrape_and_enrich.py            # Standalone scrape+enrich script
├── trigger_scrape.py               # Manual scrape trigger script
├── re_enrich_all.py                # Bulk re-enrichment script
├── re_enrich_jobs.py               # Selective re-enrichment script
├── inspect_salaries.py             # Salary data inspection utility
│
└── app/
    ├── __init__.py
    ├── config.py                   # pydantic-settings (singleton)
    ├── dependencies.py             # DI container (ports → adapters)
    ├── scheduler.py                # APScheduler + distributed cron lock
    │
    ├── domain/                     # ── Pure Data ──
    │   ├── enums.py                # UserRole, ChatStatus, MockInterviewStatus
    │   └── models.py               # 15+ Pydantic schemas
    │
    ├── ports/                      # ── Abstract Interfaces (ABCs) ──
    │   ├── ai_port.py              # generate_enrichment, chat, analyze_gap, tailor_resume, generate_blog_post, evaluate_mock_interview, extract_missing_skills
    │   ├── embedding_port.py       # encode()
    │   ├── database_port.py        # Aggregate: UserPort + JobPort + BlogPort + ChatPort + MockInterviewPort + scraping logs + learning resources
    │   ├── user_port.py            # get_user, upsert_user
    │   ├── job_port.py             # CRUD + find_by_external_id + find_by_description_hash + analytics query
    │   ├── blog_port.py            # create, list, get by slug
    │   ├── chat_port.py            # session CRUD, find, list
    │   ├── mock_interview_port.py  # interview CRUD, pending reviews
    │   ├── document_port.py        # extract_text (PDF + DOCX)
    │   ├── storage_port.py         # upload_file, get_signed_url
    │   ├── pdf_port.py             # Legacy PDF-only extraction
    │   └── scraper_port.py         # Located in app/scraper/
    │
    ├── adapters/                   # ── Concrete Implementations ──
    │   ├── openai_adapter.py       # AIPort → GPT-4o-mini (structured) + GPT-4o (writing)
    │   ├── openai_embedding.py     # EmbeddingPort → text-embedding-3-small (384d)
    │   ├── supabase_adapter.py     # DatabasePort → Supabase REST client
    │   ├── supabase_storage_adapter.py # StoragePort → Supabase Storage
    │   ├── document_adapter.py     # DocumentPort → PyPDF + python-docx (threadpooled)
    │   └── pypdf_adapter.py        # PdfPort → Legacy PDF extraction
    │
    ├── scraper/                    # ── Web Scrapers ──
    │   ├── scraper_port.py         # ScraperPort ABC: fetch_jobs()
    │   ├── base_scraper.py         # Shared logic: crawl4ai + BS4 + entry-level filter
    │   ├── experience_filter.py    # Regex-based 0–2 year filter
    │   ├── deloitte_adapter.py     # Deloitte career page parser
    │   ├── pwc_adapter.py          # PwC career page parser
    │   ├── kpmg_adapter.py         # KPMG career page parser
    │   └── ey_adapter.py           # EY career page parser
    │
    ├── agents/                     # ── AI Agents ──
    │   └── blog_agent.py           # BlogAgent: RSS news → AI blog generation
    │
    ├── services/                   # ── Business Logic ──
    │   ├── auth_service.py         # JWT decode + user resolution
    │   ├── user_service.py         # Profile + resume pipeline
    │   ├── job_service.py          # Job CRUD orchestration
    │   ├── enrichment_service.py   # AI enrichment pipeline + batch stub
    │   ├── matching_service.py     # Cosine similarity + gap analysis + skill extraction
    │   ├── chat_service.py         # Message routing + AI personalization + greeting
    │   ├── ingestion_service.py    # Scrape → dedup → insert → enrich pipeline
    │   ├── analytics_service.py    # In-memory market data aggregation
    │   ├── mock_interview_service.py # Interview flow: start → submit → evaluate → review
    │   ├── market_news_service.py  # Google News RSS for Big 4 career news
    │   └── resume_tailor.py        # Placeholder for future resume tailoring logic
    │
    └── routers/                    # ── Thin HTTP/WS Layer ──
        ├── auth.py                 # /auth/signup, /auth/login
        ├── users.py                # /users/me, /users/resume, /users/me/resume
        ├── jobs.py                 # /jobs, /jobs/feed, /jobs/{id}/details, /jobs/provider
        ├── matching.py             # /jobs/{id}/match, /jobs/{id}/tailor-resume
        ├── chat.py                 # /chat/sessions, /ws/chat/{id}, /chat/my-sessions
        ├── admin.py                # /admin/sessions, /admin/ingest, /admin/reenrich, /admin/scrape-all
        ├── ingestion.py            # /admin/ingest/all, /admin/ingest/{source}
        ├── blog.py                 # /blogs, /blogs/{slug}, /blogs/generate, /blogs/refresh-trends
        ├── analytics.py            # /analytics/market
        └── mock_interviews.py      # /mock-interviews/start, submit, review, my, details
```

---

## 4. Configuration & Environment Variables

Managed by `pydantic-settings` in `app/config.py`. Loads from `.env` with typed validation.

| Variable | Type | Description |
|---|---|---|
| `SUPABASE_URL` | `str` | Supabase project URL |
| `SUPABASE_KEY` | `str` | Anon key (client-facing) |
| `SUPABASE_SERVICE_ROLE_KEY` | `str` | Service role key (bypasses RLS) |
| `SUPABASE_JWT_SECRET` | `str` | JWT secret for token verification |
| `OPENAI_API_KEY` | `str` | OpenAI API key for AI + embeddings |
| `APP_NAME` | `str` | Defaults to `"jobs.ottobon.cloud"` |
| `DEBUG` | `bool` | Defaults to `False` |

---

## 5. Database Schema

Powered by **Supabase (PostgreSQL 15+)** with **pgvector** enabled. Tables use `_jobs` suffix for multi-app namespacing.

### 5.1 `users_jobs`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | Linked to Supabase Auth user |
| `email` | TEXT (UNIQUE) | Required |
| `role` | ENUM | `seeker`, `provider`, `admin` |
| `full_name` | TEXT | Optional display name |
| `password` | TEXT | Stored for admin API auth flow |
| `resume_text` | TEXT | Extracted text from uploaded PDF/DOCX |
| `resume_embedding` | VECTOR(384) | Generated by `text-embedding-3-small` |
| `resume_file_url` | TEXT | Storage path in `resumes` bucket |
| `resume_file_name` | TEXT | Original uploaded filename |
| `created_at` | TIMESTAMPTZ | Auto-generated |

### 5.2 `jobs_jobs`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | Auto-generated |
| `provider_id` | UUID (FK → users) | Who posted the job |
| `title` | TEXT | Required |
| `description_raw` | TEXT | Full job description |
| `skills_required` | JSONB | Array of skill strings |
| `status` | TEXT | `active`, `processing` |
| `company_name` | TEXT | For scraped jobs |
| `location` | TEXT | Job location |
| `salary_range` | TEXT | AI-estimated or explicit salary |
| `external_id` | TEXT | Unique ID from source (for dedup) |
| `external_apply_url` | TEXT | Link to apply externally |
| `description_hash` | TEXT | SHA-256 hash for AI cost dedup |
| `resume_guide_generated` | JSONB | AI: 5 resume optimization bullets |
| `prep_guide_generated` | JSONB | AI: 5 interview questions + strategies |
| `embedding` | VECTOR(384) | Job description embedding |
| `created_at` | TIMESTAMPTZ | Auto-generated |

### 5.3 `chat_sessions_jobs`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | Auto-generated |
| `user_id` | UUID (FK → users) | Session owner |
| `job_id` | UUID (FK → jobs, nullable) | Associated job for contextual coaching |
| `status` | ENUM | `active_ai`, `closed` (human takeover deprecated) |
| `conversation_log` | JSONB | Array of message objects `{role, content, timestamp, hidden?}` |
| `created_at` | TIMESTAMPTZ | Auto-generated |

### 5.4 `mock_interviews_jobs`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | Auto-generated |
| `user_id` | UUID (FK → users) | Interviewee |
| `job_id` | UUID (FK → jobs) | Target job |
| `transcript` | JSONB | Array of Q&A pairs |
| `ai_scorecard` | JSONB | `{technical_accuracy, clarity, confidence, summary_notes}` (1–10) |
| `expert_feedback` | TEXT | Optional admin review |
| `status` | ENUM | `in_progress`, `completed`, `pending_review`, `reviewed` |
| `created_at` | TIMESTAMPTZ | Auto-generated |

### 5.5 `blog_posts_jobs`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | Auto-generated |
| `title` | TEXT | Blog post title |
| `slug` | TEXT (UNIQUE) | URL-friendly identifier |
| `summary` | TEXT | 2–3 sentence teaser |
| `content` | TEXT | Full markdown article |
| `image_url` | TEXT | Hero image URL |
| `published_at` | TIMESTAMPTZ | Publication timestamp |

### 5.6 `scraping_logs_jobs`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | Auto-generated |
| `source_name` | TEXT | Scraper identifier (e.g., `deloitte`) |
| `status` | TEXT | `running`, `success`, `partial`, `failed` |
| `started_at` | TIMESTAMPTZ | Job start time |
| `finished_at` | TIMESTAMPTZ | Job end time |
| `jobs_found` | INT | Total raw jobs fetched |
| `jobs_new` | INT | New jobs inserted |
| `jobs_skipped` | INT | Duplicate jobs skipped |
| `error_count` | INT | Failed individual jobs |
| `error_message` | TEXT | Error details |
| `traceback` | TEXT | Full Python traceback |

### 5.7 `cron_locks_jobs`

| Column | Type | Notes |
|---|---|---|
| `lock_name` | TEXT (PK) | Lock identifier (e.g., `daily_ingestion`) |
| `locked_until` | TIMESTAMPTZ | Lock expiry (TTL: 30 minutes) |

### 5.8 `learning_resources_jobs`

| Column | Type | Notes |
|---|---|---|
| `skill_name` | TEXT | Skill this resource teaches |
| *other columns* | *varies* | Resource URL, title, type, etc. |

### 5.9 Storage Buckets

| Bucket | Access | Purpose |
|---|---|---|
| `resumes` | Private | Original PDF/DOCX resume files. Accessed via 15-min signed URLs. |

---

## 6. Dependency Injection System

**File:** `app/dependencies.py`

Central wiring using `@lru_cache` singletons for adapters and FastAPI `Depends()` for injection.

### Adapter Singletons

| Factory | Returns | Concrete |
|---|---|---|
| `get_ai_service()` | `AIPort` | `OpenAIAdapter(GPT-4o-mini)` |
| `get_embedding_service()` | `EmbeddingPort` | `OpenAIEmbeddingAdapter(text-embedding-3-small, 384d)` |
| `get_db()` | `DatabasePort` | `SupabaseAdapter` (service role key) |
| `get_storage()` | `StoragePort` | `SupabaseStorageAdapter` |
| `get_document_parser()` | `DocumentPort` | `DocumentAdapter` (PDF + DOCX) |

### Scraper Registry

```python
_SCRAPER_REGISTRY = {
    "deloitte": DeloitteAdapter,
    "pwc":      PwCAdapter,
    "kpmg":     KPMGAdapter,
    "ey":       EYAdapter,
}
```

- `get_scraper(name)` → resolves name to adapter instance
- `get_all_scrapers()` → list of all registered scraper instances

### Domain Service Injection

- `get_matching_service(db, ai)` → `MatchingService`
- `get_analytics_service(db)` → `AnalyticsService`

**To swap a provider:** Change a single line in `dependencies.py`. Nothing else changes.

---

## 7. Authentication Flow

**File:** `app/services/auth_service.py`

### Method: Supabase Auth (JWT) — Server-Proxied

```
Client → POST /auth/signup or /auth/login
       → Backend creates user via Supabase Admin API
       → Returns {access_token, refresh_token, user_id, email, role}

Client → Any protected endpoint
       → Sends Authorization: Bearer <access_token>
       → auth_service decodes JWT (sub claim) → extracts user_id
       → Fetches user profile from users_jobs table
       → Returns user dict for downstream use
```

### Key Details

1. **Signup** (`POST /auth/signup`): Creates user in Supabase Auth via admin API (bypasses email rate limits), auto-confirms email, creates/updates row in `users_jobs`, signs in immediately, returns tokens.
2. **Login** (`POST /auth/login`): Signs in via admin client, fetches role from `users_jobs`, returns tokens.
3. **JWT Verification**: Decodes without full signature verification (uses `verify_signature: False`, `verify_exp: True`, 30s leeway). The `sub` claim provides the user ID, which is then validated against the database.
4. **`get_current_user()`**: FastAPI dependency used by all protected endpoints. Returns the full user dict from the database.

---

## 8. API Endpoints — Complete Reference

### Auth (`/auth`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/signup` | ✗ | Register new user (auto-confirm, returns tokens) |
| `POST` | `/auth/login` | ✗ | Login (returns tokens + role) |

### Users (`/users`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/users/me` | ✓ | Get authenticated user's profile |
| `POST` | `/users/resume` | ✓ | Upload PDF/DOCX resume → store + parse + embed |
| `GET` | `/users/me/resume` | ✓ | Get 15-min signed download URL for resume |

### Jobs (`/jobs`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/jobs` | ✓ | Create job posting (202, AI enrichment runs in background) |
| `GET` | `/jobs/feed` | ✗ | Paginated public feed (`?skip=0&limit=20`) |
| `GET` | `/jobs/provider` | ✓ | List jobs created by the authenticated provider |
| `GET` | `/jobs/{id}/details` | ✗ | Full 4-Pillar job details |

### Matching (`/jobs`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/jobs/{id}/match` | ✓ | Cosine similarity match + AI gap analysis + missing skills + learning recs |
| `POST` | `/jobs/{id}/tailor-resume` | ✓ | AI rewrites resume to target the job (GPT-4o) |

### Chat (`/chat`, `/ws`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/chat/sessions` | ✓ | Create session (or return existing for job). Body: `{job_id?}` |
| `GET` | `/chat/my-sessions` | ✓ | List all sessions for current user (with job titles) |
| `GET` | `/chat/sessions/{id}` | ✓ | Get session info |
| `WS` | `/ws/chat/{session_id}` | ✗ | Real-time WebSocket chat (history replay + auto-greeting) |

### Mock Interviews (`/mock-interviews`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/mock-interviews/start` | ✓ | Start interview for a job. Body: `{job_id}` |
| `POST` | `/mock-interviews/{id}/submit` | ✓ | Submit 5 answers → AI evaluates. Body: `{answers: []}` |
| `POST` | `/mock-interviews/{id}/request-review` | ✓ | Request human expert review (204) |
| `GET` | `/mock-interviews/my` | ✓ | List all my mock interviews |
| `GET` | `/mock-interviews/{id}` | ✓ | Get full details + scorecard |

### Blog (`/blogs`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/blogs/` | ✗ | List recent blog posts (public) |
| `GET` | `/blogs/{slug}` | ✗ | Get blog post by slug (public) |
| `POST` | `/blogs/generate` | ✓ (admin) | Trigger AI blog generation from market news |
| `POST` | `/blogs/refresh-trends` | ✓ (admin) | Generate "Big 4 Campus Watch" post |

### Analytics (`/analytics`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/analytics/market` | ✓ | Aggregated market intelligence (top skills, salaries, companies, work styles, experience levels) |

### Admin (`/admin`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/admin/sessions` | ✓ (admin) | List all chat sessions with user info |
| `GET` | `/admin/sessions/{id}` | ✓ (admin) | Full session details (conversation log) |
| `POST` | `/admin/sessions/{id}/intercept` | ✓ (admin) | Inject "expert joined" notification (+ live WebSocket push) |
| `POST` | `/admin/sessions/{id}/message` | ✓ (admin) | Send message to seeker's chat (saved + live WebSocket push) |
| `POST` | `/admin/ingest/trigger` | ✓ (admin/provider) | Manual ingestion trigger (`?scraper_name=deloitte`) |
| `POST` | `/admin/ingest/all` | ✓ (admin) | Trigger global ingestion (all scrapers, background) |
| `POST` | `/admin/ingest/{source}` | ✓ (admin) | Trigger specific scraper (synchronous) |
| `POST` | `/admin/reenrich` | ✗ (dev) | Re-run AI enrichment for all unenriched jobs (batched, 3 at a time) |
| `POST` | `/admin/scrape-all` | ✗ (dev) | Scrape all sources (no auth, background) |

### Health Check

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/` | ✗ | Returns `{"status": "ok", "service": "jobs.ottobon.cloud"}` |

---

## 9. Core Pipelines — Detailed Breakdown

### Component Map: Service → Port → Adapter

| Service | Ports Used | Key Operations |
|---|---|---|
| `AuthService` | `DatabasePort` | JWT decode, user lookup |
| `UserService` | `DatabasePort`, `DocumentPort`, `EmbeddingPort`, `StoragePort` | Resume upload → parse → embed → store |
| `JobService` | `DatabasePort` | Job CRUD |
| `EnrichmentService` | `DatabasePort`, `AIPort`, `EmbeddingPort` | AI enrichment + embedding generation |
| `MatchingService` | `DatabasePort`, `AIPort` | Cosine similarity + gap analysis + skill extraction |
| `ChatService` | `DatabasePort`, `AIPort` | Message routing + personalized AI responses |
| `IngestionService` | `DatabasePort`, `AIPort`, `EmbeddingPort`, `ScraperPort` | Scrape → dedup → insert → enrich |
| `MockInterviewService` | `DatabasePort`, `AIPort` | Interview lifecycle + AI scoring |
| `AnalyticsService` | `DatabasePort` | In-memory aggregation from raw jobs |
| `MarketNewsService` | *(none)* | Google News RSS fetching + filtering |
| `BlogAgent` | `DatabasePort`, `AIPort`, `MarketNewsService` | News → AI blog post → save |

---

## 10. AI Enrichment Pipeline

**File:** `app/services/enrichment_service.py`

Triggered automatically as a **FastAPI BackgroundTask** whenever a job is created (via API or scraper).

### Flow

```
Job Created
    ↓
EnrichmentService.enrich_job(job_id)
    ↓
1. Fetch job record from DB
    ↓
2. AIPort.generate_enrichment(description, skills, title, company_name)
   → Instructor enforces AIEnrichment schema:
     • 5 resume optimization bullet points
     • 5 interview questions with answer strategies
     • Top 5-10 extracted skills
     • Estimated salary range
    ↓
3. EmbeddingPort.encode(description) → 384-d vector
    ↓
4. Update job record with:
   - resume_guide_generated (JSONB)
   - prep_guide_generated (JSONB)
   - skills_required (populated if empty)
   - embedding (VECTOR)
   - salary_range (TEXT)
```

### AI Models Used

- **Enrichment/Chat/Analysis:** GPT-4o-mini (faster, cheaper)
- **Resume Tailoring/Blog Generation:** GPT-4o (higher quality writing)
- **Embeddings:** text-embedding-3-small (384 dimensions)
- **Structured Output:** Instructor library enforces Pydantic schema compliance

### Cost Optimization: SHA-256 Dedup

During ingestion, if a new job has the same `description_hash` as an already-enriched job, the system **copies the enrichment data** rather than making another AI call. This can save ~50% on token costs for duplicate descriptions across companies.

### Batch API Stub

`enrich_jobs_batch()` is stubbed for future OpenAI Batch API integration (~50% cost reduction, 24h turnaround). Currently falls back to sequential processing.

---

## 11. Resume Processing Pipeline

**File:** `app/services/user_service.py`

### Flow

```
POST /users/resume (PDF or DOCX)
    ↓
1. Validate extension (.pdf or .docx only)
    ↓
2. Sanitize filename: "resume (1).pdf" → "resume_1.pdf"
   Generate unique path: {user_id}/{8char_uuid}_{safe_name}
    ↓
3. Upload original file to Supabase Storage (resumes bucket)
   → content_type preserved, upsert enabled
    ↓
4. Extract text via DocumentAdapter
   → PDF: pypdf (PdfReader) — offloaded to threadpool via asyncio.to_thread()
   → DOCX: python-docx (Document.paragraphs) — offloaded to threadpool
   → Minimum 50 chars required (rejects scanned/image-only documents)
    ↓
5. Generate embedding via OpenAIEmbeddingAdapter
   → text-embedding-3-small, 384 dimensions
   → Text truncated to 8000 chars for token limits
    ↓
6. Upsert user record with:
   - resume_text, resume_embedding, resume_file_url, resume_file_name
```

### Resume Download

`GET /users/me/resume` generates a **15-minute signed URL** via `SupabaseStorageAdapter.get_signed_url()`. Each request generates a fresh URL. Response includes `Cache-Control: no-store`.

---

## 12. Matching Engine & Skill Gap Analysis

**File:** `app/services/matching_service.py`

### Flow

```
POST /jobs/{id}/match
    ↓
1. Fetch user embedding + job embedding
    ↓
2. Cosine similarity calculation (pure Python, no external lib)
    ↓
3. If score ≥ 0.7: Return {similarity_score, gap_detected: false}
    ↓
4. If score < 0.7 (GAP DETECTED):
   → Run in parallel (asyncio.gather):
     a) AIPort.analyze_gap(resume_text, job_description)
        → 2-3 sentence constructive explanation
     b) AIPort.extract_missing_skills(resume_text, required_skills)
        → Instructor-enforced list of specific missing skills
   → Then: DatabasePort.get_learning_resources(missing_skills)
     → Returns curated learning resources from learning_resources_jobs table
    ↓
5. Return MatchResult:
   {job_id, similarity_score, gap_detected, gap_analysis, missing_skills, learning_recommendations}
```

### Timeout Protection

The match endpoint wraps the entire operation in `asyncio.wait_for(timeout=45.0)` to prevent hanging on slow AI/DB calls. Returns HTTP 504 on timeout.

---

## 13. Resume Tailoring (AI Rewrite)

**Endpoint:** `POST /jobs/{id}/tailor-resume`

Uses **GPT-4o** (stronger model) to rewrite the user's resume to target a specific job description:

1. Fetches the user's `resume_text` and the job's `description_raw`
2. Sends to AI with ATS-specialist system prompt:
   - Keeps candidate's truthful experiences
   - Rephrases bullet points to match JD keywords
   - Adds a "Targeted Professional Summary"
3. Returns `{tailored_resume: "...markdown..."}` 

---

## 14. Job Ingestion & Scheduling

### Scheduler

**File:** `app/scheduler.py`

- **Engine:** APScheduler `AsyncIOScheduler`
- **Schedule:** Daily at **22:00 IST** (Asia/Kolkata)
- **Trigger:** `CronTrigger(hour=22, minute=0, timezone="Asia/Kolkata")`
- **Lifecycle:** Started via FastAPI lifespan events in `main.py`

### Distributed Lock

Prevents duplicate cron runs across multiple Uvicorn workers:

1. Uses PostgreSQL `cron_locks_jobs` table
2. `acquire_cron_lock()` calls Supabase RPC (`acquire_cron_lock`) for atomic upsert
3. Lock TTL: 30 minutes (auto-expires if worker crashes)
4. Lock released after ingestion completes (even on failure)
5. Falls back to permissive mode if table doesn't exist (backward compat)

### Ingestion Pipeline

**File:** `app/services/ingestion_service.py`

```
trigger_ingestion(scraper_name?)
    ↓
For each scraper:
    ↓
1. Create scraping_log entry (status: "running")
    ↓
2. scraper.fetch_jobs()
   → If fails: log error, update log to "failed", move to next scraper
    ↓
3. For each job:
   a) Dedup by (company_name, external_id)
      → Skip if exists
   b) Insert job (status: "processing")
   c) Compute SHA-256 hash of description_raw
   d) Check for existing enriched job with same hash:
      → HIT: Copy enrichment data, set status "active" (saves AI call)
      → MISS: Run full EnrichmentService.enrich_job(), set status "active"
    ↓
4. Update scraping_log with stats:
   {fetched, new, skipped, errors, dedup_hits}
   Status: "success" | "partial" | "failed"
```

### System Provider User

All scraped jobs are owned by a fixed UUID: `00000000-0000-4000-a000-000000000001` (the system-level "ingestion provider").

---

## 15. Web Scraper System

### Architecture

```
ScraperPort (ABC)
    ↑
BaseScraper                    # Shared: crawl4ai + BS4 + entry-level filter
    ↑
    ├── DeloitteAdapter        # parse_jobs() for Deloitte career page
    ├── PwCAdapter             # parse_jobs() for PwC career page
    ├── KPMGAdapter            # parse_jobs() for KPMG career page
    └── EYAdapter              # parse_jobs() for EY career page
```

### BaseScraper Flow

1. `crawl4ai.AsyncWebCrawler` renders the JS-heavy career page (Playwright under the hood)
2. `BeautifulSoup` parses the HTML
3. `self.parse_jobs(soup)` → subclass extracts raw job cards
4. `experience_filter.is_entry_level()` filters to 0–2 year roles only
5. Returns normalized dicts with: `external_id`, `title`, `company_name`, `external_apply_url`, `description_raw`, `skills_required`, `location`, `salary_range`

### Experience Filter

Rejects: `senior`, `manager`, `director`, `vp`, `principal`, `lead`, `head`, `architect`, `partner`, `chief`  
Accepts: `analyst`, `associate`, `intern`, `trainee`, `fresher`, `graduate`, `entry`, `junior`, `apprentice`  
Also checks experience text for "0-2 years", "fresher", "entry level" patterns via regex.  
**Default: accepts** (to maximize coverage during early phases).

---

## 16. Control Tower — WebSocket Chat System

**Files:** `app/routers/chat.py`, `app/services/chat_service.py`

### Session Lifecycle

```
1. POST /chat/sessions {job_id?}
   → Finds existing active session for user+job, or creates new one
   → If job_id provided: seeds conversation_log with hidden job context
      {role: "system", hidden: true, job_id, job_title, job_description, skills_required}

2. WS /ws/chat/{session_id}
   → On connect:
     a) Validate session exists and is not closed
     b) Replay last 10 messages (state recovery for reconnects)
     c) If empty session: generate personalized AI greeting
   → Main loop:
     a) Receive text (ignores "__ping__" heartbeats and empty messages)
     b) ChatService.handle_message() builds full context:
        - Appends user message to log
        - Builds user_context from profile (name, resume snippet, skills)
        - Sends full history to AIPort.chat() with personalized system prompt
     c) Returns AI reply via {type: "ai_reply", content: "..."}

3. Admin intercept (status remains active_ai):
   → POST /admin/sessions/{id}/intercept injects "expert joined" notification
   → POST /admin/sessions/{id}/message sends admin message
   → Both save to conversation_log AND push live via WebSocket
```

### ConnectionManager

In-memory WebSocket manager keyed by `session_id`. Production note: should be replaced with Redis Pub/Sub for horizontal scaling.

### AI Personalization

The chat system injects rich context into the AI system prompt:
- User's name
- Resume text (truncated to 2000 chars)
- User's skills
- Job title (if session is job-specific)

---

## 17. Mock Interview System

**Files:** `app/services/mock_interview_service.py`, `app/routers/mock_interviews.py`

### Flow

```
1. POST /mock-interviews/start {job_id}
   → Validates job has prep_guide_generated (5 questions)
   → Creates mock_interviews_jobs record (status: in_progress)

2. POST /mock-interviews/{id}/submit {answers: ["...", "...", ...]}
   → Matches each answer to corresponding prep question
   → Builds transcript: [{role: "assistant", content: Q}, {role: "user", content: A}, ...]
   → AIPort.evaluate_mock_interview(transcript, job_description)
   → Instructor enforces MockScorecard schema:
     - technical_accuracy: 1-10
     - clarity: 1-10
     - confidence: 1-10
     - summary_notes: constructive feedback
   → Updates record with transcript + scorecard (status: completed)

3. POST /mock-interviews/{id}/request-review
   → Sets status to pending_review (for admin dashboard)

4. GET /mock-interviews/my
   → Lists all interviews with job titles (Supabase join)

5. GET /mock-interviews/{id}
   → Full details including scorecard
```

---

## 18. Blog Generation Agent

**File:** `app/agents/blog_agent.py`

### Flow

```
POST /blogs/generate (admin only)
    ↓
1. MarketNewsService.fetch_big4_career_news(limit=5)
   → Fetches from Google News RSS (see §19)
    ↓
2. Constructs prompt: "Act as Career Strategist for university students..."
   → News articles formatted as context
   → Instructs: Don't summarize → translate to Student Actions
   → Structure: Title, Executive Summary, News & Opportunities, Action Plan
    ↓
3. AIPort.generate_blog_post(prompt)
   → GPT-4o with JSON response format
   → Returns {slug, title, summary, content (markdown)}
    ↓
4. Adds default hero image URL
5. Saves to blog_posts_jobs table
```

---

## 19. Market News Service (RSS)

**File:** `app/services/market_news_service.py`

### How It Works

1. **Query Construction:** `(Deloitte OR PwC OR KPMG OR EY) AND ("intern" OR "internship" OR "graduate" OR ...)`
2. **Source:** Google News RSS feed (`news.google.com/rss/search`)
3. **Filtering:**
   - Must mention at least one Big 4 company
   - Must NOT contain exclude keywords: `stock`, `share price`, `dividend`, `revenue`, `lawsuit`, etc.
   - Must contain a career keyword: `intern`, `internship`, `graduate`, `early career`, `campus`, `hiring`, etc.
4. **Deduplication:** By title
5. **Returns:** `{title, link, summary, published, source}` for up to 5 articles

---

## 20. Analytics & Market Intelligence

**File:** `app/services/analytics_service.py`

### Endpoint: `GET /analytics/market`

Fetches all active jobs from DB and performs **in-memory aggregation**:

| Metric | Logic |
|---|---|
| `total_jobs` | Count of all active jobs |
| `top_skills` | Counter of all `skills_required` values, top 10, title-cased |
| `top_companies` | Counter of `company_name`, top 5 |
| `salary_trends` | Groups by normalized title, parses salary strings (`$100k - $150k`), computes `avg_min` / `avg_max`, top 8 roles |
| `work_styles` | Classifies jobs as Remote/Hybrid/On-site based on location and title keywords |
| `experience_levels` | Classifies by title: Senior/Lead, Junior/Entry, Mid-Level, Internship, Not Specified |

### Title Normalization

Simplifies titles for grouping: "Senior Backend Engineer (Remote)" → "Backend Engineer". Maps to canonical categories: Full Stack Developer, Backend Engineer, Data Scientist, DevOps / SRE, etc.

---

## 21. Admin Dashboard API

### Session Management

- **View all sessions:** `GET /admin/sessions` — Returns sessions with user info (email, name)
- **Session details:** `GET /admin/sessions/{id}` — Full conversation log
- **Intercept:** `POST /admin/sessions/{id}/intercept` — Injects "🛡️ An expert has joined" system notification + WebSocket push
- **Send message:** `POST /admin/sessions/{id}/message` — Admin message saved to log + pushed live to seeker

### Ingestion Controls

- **Trigger specific:** `POST /admin/ingest/{source_name}` — Synchronous, returns stats
- **Trigger all:** `POST /admin/ingest/all` — Background task
- **Trigger via scheduler:** `POST /admin/ingest/trigger?scraper_name=deloitte` — Background, admin or provider
- **Scrape all (dev):** `POST /admin/scrape-all` — No auth, background

### Re-Enrichment

`POST /admin/reenrich` — Processes in batches of 3 jobs with 3-second delays between batches. Finds all jobs missing `prep_guide_generated`, `resume_guide_generated`, or `embedding`.

---

## 22. Deployment

### Docker

```dockerfile
FROM python:3.12-slim
# Includes Playwright + Chromium for web scraping
# Exposes port 8200
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8200"]
```

### Docker Compose

```yaml
services:
  backend:
    build: .
    container_name: ottobon-jobs-backend
    restart: always
    ports:
      - "8200:8200"
    env_file:
      - .env
    volumes:
      - .:/app
```

### Run

```bash
docker compose up --build -d
```

---

## 23. Setup & Run Instructions

### Local Development

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create virtual environment
py -3.12 -m venv venv

# 3. Activate (PowerShell)
.\venv\Scripts\Activate.ps1

# 4. Install dependencies
pip install -r requirements.txt

# 5. Install Playwright browsers (required for scrapers)
playwright install

# 6. Setup environment
copy .env.example .env
# Edit .env with your Supabase + OpenAI credentials

# 7. Run server (with hot reload)
python -m uvicorn main:app --reload

# Server will be available at http://127.0.0.1:8000
# Scheduler will start automatically (next run shown in logs)
```

### ⚠️ Common Issue: Stale venv Path

If you get a "Fatal error in launcher" when running `uvicorn` directly, the venv was created at a different path. Use `python -m uvicorn` instead.

---

## 24. Dependencies

| Package | Version | Purpose |
|---|---|---|
| `fastapi[standard]` | ≥0.115.0 | Web Framework + Uvicorn |
| `uvicorn[standard]` | ≥0.30.0 | ASGI Server |
| `supabase` | ≥2.0.0 | Database, Auth, Storage client |
| `python-jose[cryptography]` | ≥3.3.0 | JWT decoding |
| `pydantic-settings` | ≥2.0.0 | Typed environment config |
| `openai` | ≥1.40.0 | AI completions + embeddings |
| `instructor` | ≥1.5.0 | Structured AI output (Pydantic schema enforcement) |
| `pypdf` | ≥4.0.0 | PDF text extraction |
| `python-docx` | ≥1.1.0 | DOCX text extraction |
| `python-multipart` | ≥0.0.9 | File upload parsing |
| `httpx` | ≥0.27.0 | Async HTTP client |
| `apscheduler` | ≥3.10.0 | Scheduled background tasks |
| `beautifulsoup4` | ≥4.12.0 | HTML parsing for scrapers |
| `crawl4ai` | ≥0.4.0 | Headless browser for JS-rendered pages (Playwright) |
| `feedparser` | ≥6.0.0 | Google News RSS feed parsing |

---

## 25. Database Migrations

Located in `migrations/`. Run manually via Supabase SQL editor.

| File | Purpose |
|---|---|
| `003_cron_locks.sql` | Creates `cron_locks_jobs` table + `acquire_cron_lock` RPC function |
| `004_blog_posts.sql` | Creates `blog_posts_jobs` table |
| `004_hnsw_index.sql` | HNSW index on pgvector embeddings for fast similarity search |
| `005_add_archived_at.sql` | Adds `archived_at` column to jobs |
| `005_rls_policies.sql` | Row Level Security policies for all tables |
| `006_learning_resources.sql` | Creates `learning_resources_jobs` table |
| `006_setup_blog_and_seed.sql` | Blog table setup + seed data |
| `007_mock_interviews.sql` | Creates `mock_interviews_jobs` table |
| `add_password_column.sql` | Adds `password` column to `users_jobs` |
| `data_migration_to_org.sql` | Data migration for multi-org namespacing |
| `org_schema_setup.sql` | Full schema setup with `_jobs` table suffixes |

---

## 26. Production Hardening Notes

| Area | Implementation |
|---|---|
| **CORS** | Fully open (`allow_origins=["*"]`). Tighten for production. |
| **Global Exception Handler** | All unhandled errors return proper JSON with CORS headers. Prevents browser connection errors. |
| **CPU Offloading** | PDF/DOCX parsing runs in `asyncio.to_thread()` threadpool to avoid blocking the event loop. |
| **Distributed Cron Lock** | PostgreSQL-backed lock prevents duplicate scheduler runs across workers. 30-min TTL auto-release. |
| **Scraper Resilience** | Fail-fast per-scraper: if one fails, others continue. Full traceback logged to `scraping_logs_jobs`. |
| **SHA-256 Dedup** | Copies enrichment data for duplicate job descriptions instead of re-running AI. |
| **WebSocket Recovery** | History replay (last 10 messages) on reconnect. Heartbeat support (`__ping__`/`__pong__`). |
| **Match Timeout** | 45-second timeout on match endpoint to prevent hanging. |
| **Text Truncation** | Resume text (2000–4000 chars) and job descriptions (3000–4000 chars) truncated before AI calls to control token costs. |
| **Embedding Truncation** | Input text truncated to 8000 chars before embedding to stay within token limits. |
| **Re-enrichment Throttling** | Batch processing (3 jobs at a time, 3s delay) to avoid overloading the server. |
| **Scanned PDF Rejection** | Documents with <50 chars extracted text are rejected with a helpful error. |
| **Filename Sanitization** | Special characters removed, spaces replaced with underscores, UUID prefix for uniqueness. |

---

## 27. RAG Document Pipeline (OneDrive + Celery)

A fully decoupled, asynchronous background processing pipeline for handling large document uploads (PDF, DOCX) and preparing them for Retrieval-Augmented Generation (RAG).

### Architecture
* **FastAPI Router (`app/routers/rag.py`)**: Accepts multipart file uploads, validates extensions, and immediately returns a `doc_id` to the client so the UI doesn't block.
* **Database (`jobs_resumes`)**: Tracks the document lifecycle (`status`: `uploading` -> `uploaded` -> `indexing` -> `ready` -> `failed`). Updated via the Supabase REST API (bypassing raw PostgreSQL TCP connections).
* **Storage (Microsoft Graph)**: Files are uploaded directly to an Administrative Microsoft OneDrive folder (`ONEDRIVE_FOLDER`) using App-Only OAuth2 `client_credentials` flow.
* **Background Worker (`app/tasks/rag_tasks.py`)**: A Celery worker listening on a Redis queue picks up the `doc_id`, pulls the file, and processes the heavy ML/embedding operations asynchronously.

### Environment Variables
Requires an Azure App Registration with **`Files.ReadWrite.All`** Application permissions (Admin Consent required).
```env
MSGRAPH_CLIENT_ID=...
MSGRAPH_CLIENT_SECRET=...     # Must be the Secret Value, not the Secret ID
MSGRAPH_TENANT_ID=...
MSGRAPH_USER_ID=...           # The Object ID of the User who owns the target OneDrive
ONEDRIVE_FOLDER=jobs_platform # Root folder name where resumes are stored

CELERY_BROKER_URL=redis://localhost:6379/0
```

### Endpoints
* **`POST /rag/upload-document`**
  * **Input**: `multipart/form-data` containing the file.
  * **Flow**:
    1. Inserts a new row in `jobs_resumes` with `status: uploading`.
    2. Uploads the file via `PUT https://graph.microsoft.com/v1.0/users/{user_id}/drive/root:/{folder}/{filename}:/content`.
    3. Updates the DB with the returned `file_id`, `url`, and `status: uploaded`.
    4. Dispatches the `process_rag_document.delay(doc_id)` Celery task.
    5. Returns `200 OK` with the `doc_id` and OneDrive `url`.

### Running the Worker
Celery requires a Redis server running locally. Start the background worker process in a separate terminal:
```bash
python -m celery -A app.tasks.rag_tasks worker --loglevel=info -P gevent
```
