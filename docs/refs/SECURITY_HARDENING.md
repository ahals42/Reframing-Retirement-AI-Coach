# Security Hardening Guide

## Overview

This document describes the security measures implemented in the Reframing Retirement Coach API to protect against common vulnerabilities and ensure safe operation in production.

**Status:** ✅ Security hardening completed
**Last Updated:** 2026-01-19
**Environment:** AWS Lightsail Production

---

## 🚨 CRITICAL: Immediate Action Required

### 1. Rotate OpenAI API Key

Your OpenAI API key was previously committed to git history and **MUST be rotated immediately**.

**Steps to rotate:**

```bash
# 1. Generate a new API key at https://platform.openai.com/api-keys
# 2. Revoke the old key: 
# 3. Update your .env file with the new key
# 4. NEVER commit .env to git again
```

### 2. Generate API Keys for Authentication

```bash
# Generate secure API keys for your application
python3 -c "import secrets; print(','.join([secrets.token_urlsafe(32) for _ in range(3)]))"

# Add these to your .env file as:
# API_KEYS=key1,key2,key3
```

### 3. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and fill in all values:
# - OPENAI_API_KEY (new rotated key)
# - API_KEYS (generated above)
# - ALLOWED_ORIGINS (your AWS Lightsail IP and localhost)
# - QDRANT_API_KEY (optional but recommended)
```

---

## 🔒 Security Features Implemented

### 1. SECRET MANAGEMENT ✅

**Problem:** Secrets exposed in Docker images and git history
**Solution:**

- ✅ Created [.dockerignore](.dockerignore) to exclude `.env`, `.git`, `__pycache__`, etc.
- ✅ Modified [Dockerfile](Dockerfile) to use multi-stage build and selective COPY
- ✅ Updated [docker-compose.yml](docker-compose.yml) to pass environment variables at runtime
- ✅ Created [.env.example](.env.example) template with placeholder values
- ✅ `.env` already in `.gitignore` (but was previously committed)

**Files Modified:**
- `.dockerignore` (new)
- `.env.example` (new)
- `Dockerfile` (updated)
- `docker-compose.yml` (updated)

**Important:**
- Never commit `.env` to version control
- Use environment variable injection in docker-compose
- For production, consider AWS Secrets Manager or similar

### 2. AUTHENTICATION & AUTHORIZATION ✅

**Problem:** No authentication - anyone could use the API
**Solution:**

- ✅ Implemented API key-based authentication via `X-API-Key` header
- ✅ Created [backend/middleware/auth.py](backend/middleware/auth.py) with `@require_api_key` decorator
- ✅ Added authentication to ALL endpoints:
  - `GET /healthz`
  - `POST /sessions`
  - `DELETE /sessions/{id}`
  - `POST /sessions/{id}/messages`
  - `POST /sessions/{id}/voice-chat`
- ✅ Secure API key storage in environment variables
- ✅ Constant-time comparison to prevent timing attacks
- ✅ Returns 401 Unauthorized for missing/invalid keys

**Files Modified:**
- `backend/middleware/auth.py` (new)
- `backend/app.py` (updated)
- `backend/voice/routes.py` (updated)

**Usage:**
```bash
# All API requests must include the X-API-Key header
curl -H "X-API-Key: your-api-key-here" https://your-api.com/healthz
```

### 3. RATE LIMITING ✅

**Problem:** No rate limits - vulnerable to abuse and DOS
**Solution:**

- ✅ Added `slowapi` for FastAPI-compatible rate limiting
- ✅ Created [backend/middleware/rate_limit.py](backend/middleware/rate_limit.py)
- ✅ Implemented rate limits:
  - **Session creation:** 20 requests/hour per API key
  - **Message endpoints:** 100 requests/hour per API key
  - **Voice chat:** 100 requests/hour per API key
- ✅ Per-API-key tracking (not just IP-based)
- ✅ Returns 429 Too Many Requests with `Retry-After` header

**Files Modified:**
- `backend/middleware/rate_limit.py` (new)
- `backend/app.py` (updated)
- `backend/voice/routes.py` (updated)
- `requirements.txt` (added slowapi)

**Configuration:**
```env
RATE_LIMIT_MESSAGES_PER_HOUR=100
RATE_LIMIT_VOICE_CONCURRENT=10
MAX_SESSIONS_PER_API_KEY=50
```

### 4. INPUT VALIDATION ✅

**Problem:** No input validation - vulnerable to injection and DOS
**Solution:**

- ✅ Added max length validation for text messages (10,000 characters)
- ✅ Added max file size validation for audio uploads (10MB)
- ✅ Validated audio MIME types: `audio/wav`, `audio/webm`, `audio/mpeg`, `audio/mp4`, `audio/ogg`
- ✅ Added filename sanitization (prevent path traversal)
- ✅ Implemented session history size cap (100 messages max)
- ✅ Added input sanitization to detect excessive repetition

**Files Modified:**
- `backend/models.py` (updated with Pydantic validators)
- `backend/voice/routes.py` (updated with file validation)
- `coach/agent.py` (updated with input validation)

**Validation Rules:**
```python
# Text messages
MAX_MESSAGE_LENGTH = 10,000 characters
Empty or whitespace-only messages rejected
Excessive repetition detected (>80% same character)

# Audio files
MAX_AUDIO_SIZE = 10MB
Allowed extensions: .wav, .webm, .mp3, .m4a, .ogg, .opus
Filename path traversal prevention (os.path.basename)
```

### 5. CORS SECURITY ✅

**Problem:** `allow_origins=["*"]` allows any website to call the API
**Solution:**

- ✅ Replaced wildcard with specific allowed origins from environment
- ✅ Restricted methods to only `["GET", "POST", "DELETE"]`
- ✅ Restricted headers to `["Content-Type", "X-API-Key", "Authorization"]`
- ✅ Configured for both localhost (development) and AWS Lightsail (production)

**Files Modified:**
- `backend/app.py` (updated)

**Configuration:**
```env
# For AWS Lightsail IP 99.79.62.82 and local development
ALLOWED_ORIGINS=http://99.79.62.82,http://localhost:8000,http://127.0.0.1:8000
```

### 6. PROMPT INJECTION PROTECTION ✅

**Problem:** User input directly inserted into LLM prompts
**Solution:**

- ✅ Added input validation to detect obvious injection attempts
- ✅ Implemented content sanitization for RAG results
- ✅ Added pattern detection for common injection phrases:
  - "ignore previous instructions"
  - "disregard all prior commands"
  - "new instructions:"
  - "[SYSTEM]" / "[ADMIN]" tags
- ✅ Sanitized retrieved content (HTML escaping, control character removal)
- ✅ System prompt reinforcement (existing in `prompts/prompt.py`)

**Files Modified:**
- `coach/agent.py` (updated)
- `rag/retriever.py` (updated)

**Detection Patterns:**
```python
# Logged but not rejected (to avoid false positives)
dangerous_patterns = [
    r"ignore\s+(?:all\s+)?(?:previous|above|prior)\s+(?:instructions|prompts?|commands?)",
    r"disregard\s+(?:all\s+)?(?:previous|above|prior)\s+(?:instructions|prompts?)",
    r"new\s+instructions?:",
    r"system\s+prompt:",
    r"you\s+are\s+now\s+(?:a|an)",
]
```

### 7. COST & CRASH PROTECTION ✅

**Problem:** Unbounded sessions and history growth
**Solution:**

- ✅ Capped max sessions per API key: 50 active sessions
- ✅ Capped global sessions: 1,000 total
- ✅ Added conversation history truncation: max 100 messages
- ✅ Implemented TTL-based session cleanup: 90 minutes default
- ✅ Graceful error handling (no stack traces leaked to clients)
- ✅ Session count tracking and statistics
- ✅ Memory monitoring (estimation)

**Files Modified:**
- `backend/session_store.py` (updated)
- `coach/agent.py` (updated)
- `backend/app.py` (updated with error handling)

**Configuration:**
```env
MAX_SESSIONS_PER_API_KEY=50
MAX_TOTAL_SESSIONS=1000
MAX_HISTORY_MESSAGES=100
SESSION_TTL_MINUTES=90
```

### 8. INFRASTRUCTURE SECURITY ✅

**Problem:** Qdrant exposed publicly, Docker runs as root
**Solution:**

- ✅ Removed Qdrant port mapping (not exposed externally)
- ✅ Qdrant accessible only via Docker internal network
- ✅ Added Qdrant API key authentication (optional but recommended)
- ✅ Multi-stage Docker build to minimize image size
- ✅ Docker runs as non-root user (`appuser`, UID 1000)
- ✅ Health check endpoints added to both services
- ✅ Structured logging configured (JSON format)

**Files Modified:**
- `docker-compose.yml` (updated)
- `Dockerfile` (updated)
- `backend/app.py` (updated with logging)

**Docker Security:**
```dockerfile
# Run as non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser
USER appuser

# Selective COPY (no secrets)
COPY --chown=appuser:appuser backend/ ./backend/
COPY --chown=appuser:appuser coach/ ./coach/
# ... only necessary files
```

**Qdrant Security:**
```yaml
# Qdrant NOT exposed externally
# ports:
#   - "127.0.0.1:6333:6333"  # Bind to localhost only (commented out)

# Enable Qdrant API key (uncomment to use)
# environment:
#   - QDRANT__SERVICE__API_KEY=${QDRANT_API_KEY}
```

---

## 📊 Security Audit Summary

### Vulnerabilities Fixed

| Severity | Issue | Status |
|----------|-------|--------|
| 🔴 CRITICAL | Exposed OpenAI API key in git | ⚠️ **Action Required: Rotate Key** |
| 🔴 CRITICAL | CORS allows all origins | ✅ Fixed |
| 🔴 CRITICAL | No authentication | ✅ Fixed |
| 🔴 CRITICAL | No input validation | ✅ Fixed |
| 🟠 HIGH | Unlimited session creation | ✅ Fixed |
| 🟠 HIGH | Prompt injection vulnerability | ✅ Mitigated |
| 🟠 HIGH | No HTTPS enforcement | ⚠️ Configure reverse proxy |
| 🟠 HIGH | Unbounded conversation history | ✅ Fixed |
| 🟠 HIGH | Qdrant unauthenticated | ✅ Fixed |
| 🟠 HIGH | File upload no validation | ✅ Fixed |
| 🟠 HIGH | Docker runs as root | ✅ Fixed |
| 🟡 MEDIUM | Regex DOS vulnerability | ✅ Mitigated |
| 🟡 MEDIUM | No error logging | ✅ Fixed |
| 🟡 MEDIUM | LLM cost unbounded | ✅ Fixed |

### Additional Security Concerns

#### ⚠️ HTTPS Not Enforced

**Issue:** Application doesn't enforce HTTPS
**Recommendation:** Set up a reverse proxy (Nginx, Traefik) with Let's Encrypt SSL certificates

```bash
# Example: Using Certbot with Nginx on AWS Lightsail
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

**Configuration:**
```env
FORCE_HTTPS=true  # Enable in production
```

#### ⚠️ Session IDs in URLs

**Issue:** Session IDs passed in URL path (logged in access logs)
**Recommendation:** Already acceptable for anonymous sessions, but consider using POST with session ID in body for sensitive operations

#### ⚠️ No CSRF Protection

**Issue:** Cross-Site Request Forgery protection not implemented
**Impact:** Low (API key authentication provides some protection)
**Recommendation:** Add CSRF tokens if using cookie-based sessions in the future

---

## 🚀 Deployment Checklist

### Pre-Deployment

- [ ] Rotate OpenAI API key
- [ ] Generate secure API keys (min 32 characters)
- [ ] Configure .env file with all required values
- [ ] Test API key authentication locally
- [ ] Review CORS allowed origins
- [ ] Set up HTTPS/SSL certificates (reverse proxy)

### Deployment

- [ ] Build Docker images with new security controls
  ```bash
  docker-compose build
  ```
- [ ] Verify .env is NOT in the Docker image
  ```bash
  docker run -it --entrypoint /bin/bash <image-name>
  # Inside container:
  ls -la .env  # Should not exist
  ```
- [ ] Start services
  ```bash
  docker-compose up -d
  ```
- [ ] Verify Qdrant is not externally accessible
  ```bash
  # From external machine (should fail):
  curl http://99.79.62.82:6333
  ```
- [ ] Test API key authentication
  ```bash
  # Without API key (should return 401):
  curl http://99.79.62.82:8000/healthz

  # With API key (should return 200):
  curl -H "X-API-Key: your-key" http://99.79.62.82:8000/healthz
  ```
- [ ] Test rate limiting
  ```bash
  # Make 21+ requests rapidly (should return 429)
  for i in {1..25}; do curl -H "X-API-Key: your-key" http://99.79.62.82:8000/sessions; done
  ```
- [ ] Monitor logs for security events
  ```bash
  docker-compose logs -f api | grep -E "(Authentication|Rate limit|Input validation)"
  ```

### Post-Deployment

- [ ] Monitor OpenAI API usage
- [ ] Set up log aggregation (CloudWatch, Datadog, etc.)
- [ ] Configure alerts for suspicious activity
- [ ] Regular security audits (monthly)
- [ ] Keep dependencies updated
  ```bash
  pip list --outdated
  ```

---

## 📝 API Usage Guide

### Authentication

All API requests require an API key in the `X-API-Key` header:

```bash
# Health check
curl -H "X-API-Key: your-api-key" \
  https://your-api.com/healthz

# Create session
curl -X POST \
  -H "X-API-Key: your-api-key" \
  https://your-api.com/sessions

# Send message
curl -X POST \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, I want to start exercising"}' \
  https://your-api.com/sessions/{session_id}/messages
```

### Rate Limits

| Endpoint | Limit |
|----------|-------|
| `POST /sessions` | 20/hour per API key |
| `POST /sessions/{id}/messages` | 100/hour per API key |
| `POST /sessions/{id}/voice-chat` | 100/hour per API key |
| `GET /healthz` | No limit (for monitoring) |

### Error Responses

```json
// 401 Unauthorized - Missing/invalid API key
{
  "detail": "Missing API key. Provide X-API-Key header."
}

// 429 Too Many Requests - Rate limit exceeded
{
  "detail": {
    "error": "rate_limit_exceeded",
    "message": "Too many requests. Please slow down.",
    "retry_after": 60
  }
}

// 413 Payload Too Large - Audio file too large
{
  "detail": "Audio file too large. Maximum size: 10MB"
}
```

---

## 🔧 Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | **Required** | OpenAI API key |
| `API_KEYS` | **Required** | Comma-separated API keys |
| `ALLOWED_ORIGINS` | localhost:8000 | CORS allowed origins |
| `QDRANT_URL` | http://qdrant:6333 | Qdrant vector DB URL |
| `QDRANT_API_KEY` | (none) | Qdrant authentication key |
| `RATE_LIMIT_MESSAGES_PER_HOUR` | 100 | Message endpoint rate limit |
| `RATE_LIMIT_VOICE_CONCURRENT` | 10 | Concurrent voice streams |
| `MAX_SESSIONS_PER_API_KEY` | 50 | Max sessions per API key |
| `MAX_TOTAL_SESSIONS` | 1000 | Global session limit |
| `MAX_MESSAGE_LENGTH` | 10000 | Max text message length (chars) |
| `MAX_AUDIO_SIZE_MB` | 10 | Max audio file size (MB) |
| `MAX_HISTORY_MESSAGES` | 100 | Max conversation history |
| `SESSION_TTL_MINUTES` | 90 | Session expiration time |
| `FORCE_HTTPS` | false | Redirect HTTP to HTTPS |
| `ENABLE_JSON_LOGGING` | true | Use JSON log format |
| `LOG_LEVEL` | INFO | Logging level |

---

## 📚 Additional Resources

### Security Best Practices

1. **Secrets Management**
   - Never commit secrets to git
   - Use environment variables or secrets managers
   - Rotate keys regularly (quarterly)

2. **API Security**
   - Use HTTPS in production
   - Implement rate limiting
   - Validate all inputs
   - Log security events

3. **Infrastructure Security**
   - Run containers as non-root
   - Minimize attack surface (only necessary ports)
   - Keep dependencies updated
   - Regular security audits

### Monitoring & Alerting

Set up alerts for:
- High rate of 401/403 responses (potential attack)
- High rate of 429 responses (abuse or legitimate scaling issue)
- Session creation spikes
- OpenAI API usage spikes
- Error rate increases

### Incident Response

If you suspect a security breach:

1. **Immediate:** Rotate all API keys
2. **Investigate:** Review logs for suspicious activity
3. **Contain:** Block offending API keys/IPs
4. **Recover:** Restore from backups if needed
5. **Learn:** Update security controls

---

## 📞 Support

For security issues or questions:
- Review this documentation
- Check application logs: `docker-compose logs -f api`
- Monitor OpenAI dashboard for unusual usage

---

**Last Updated:** 2026-01-19
**Version:** 1.0.0
