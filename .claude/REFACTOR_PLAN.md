# Refactor & Security Improvement Plan

Work through each phase in order. Commit and test between each phase.
Update log goes in: updates/ (local only, gitignored)

---

## Phase 1: Security Fixes — COMPLETE ✓ (committed 2026-03-05)
- [x] Fix `sessionStorage` API key exposure in `frontend/app.js`
- [x] Fix `sessionStorage` API key exposure in `frontend/dev-auth.js`
- [x] Fix env var typo `OPENAI_API_key` → `OPENAI_API_KEY` in `rag/config.py`
- [x] Remove unused `JSONResponse` import in `backend/middleware/auth.py`
- [x] Replace `print()` with `logger.warning()` in `backend/app.py`

## Phase 2: Dead Code Removal — PENDING
All in `backend/middleware/rate_limit.py`:
- [ ] Remove `check_session_limit()` (lines 99–114)
- [ ] Remove `check_concurrent_streams()` (lines 117–132)
- [ ] Remove `SessionLimitExceeded` / `ConcurrentStreamLimitExceeded` exceptions (lines 135–142)
- [ ] Remove dead `rate_limit_exceeded_handler()` (lines 145–171)
- [ ] Remove `TokenUsageTracker` class + `token_tracker` instance (lines 175–244)
- [ ] Remove unused `get_stats()` in `backend/session_store.py` (line 145)
- [ ] Remove no-op `pool = pool` in `coach/agent.py` (line 602)

## Phase 3: Duplicate Code Consolidation — PENDING
- [ ] Merge duplicate `_infer_activity_type()` into shared utility (`rag/parsing_activities.py` + `rag/parsing_home.py`)
- [ ] Extract shared API key prefix helper in `backend/middleware/rate_limit.py` (lines 57-60, 76-77)
- [ ] Extract shared `_retrieve_and_wrap()` in `rag/retriever.py` (methods at lines 225, 247, 295)
- [ ] Move regex pattern compilation to module level in `coach/agent.py` (lines 116-124)

## Phase 4: Code Quality — PENDING
- [ ] Replace `print()` with `logger.error()` in `scripts/cli.py:25`
- [ ] Add Qdrant connection validation in `rag/retriever.py` constructor
- [ ] Standardise error message style in `backend/voice/routes.py`

---

## Completed
_(move items here after each commit)_
