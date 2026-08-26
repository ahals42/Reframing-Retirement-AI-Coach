# Tech Decisions — Reframing Retirement

Every architectural and technology choice in this project, and why it was made that way.

---

## Request Lifecycle

### What would you change if starting today?

**Pydantic Settings for config validation.** Swapping `app_config.py` for Pydantic Settings means a misconfigured environment variable fails loudly at startup rather than silently causing a feature to break mid-session. One dependency, minimal code change, genuinely useful in a deployed app.

**Gunicorn with Uvicorn workers.** The current setup runs a single Uvicorn process, which means only one CPU core is used regardless of what the Lightsail instance has. Adding Gunicorn as a process manager with multiple Uvicorn workers is a one-line change to the `CMD` in the Dockerfile and would fully saturate the instance under concurrent load.

**Embedding similarity router instead of keyword/regex.** The regex approach works for the current query space but breaks on phrasing it hasn't seen. An embedding similarity router compares the query against short descriptions of each collection and picks the closest match, which handles natural variation without an LLM call. Fast, robust, and no ongoing maintenance of regex patterns as content grows.

**Re-evaluate the chat model.** GPT-4.1-mini has better instruction following than GPT-4o-mini at comparable cost. For an app with a dense, structured system prompt encoding behaviour-change protocols, instruction adherence is directly valuable. The model name is a single config value.

**Re-benchmark the embedding model.** `text-embedding-3-large` was the right call at the time, but the embedding model landscape has moved. Newer models may close the quality gap with -3-large at lower cost or fewer dimensions. Worth running a retrieval accuracy benchmark before the next content ingest, not before.

---

### Walk me through what happens on a single chat turn.

1. Request arrives at FastAPI. The API key middleware validates the `X-API-Key` header; slowapi checks the rate limit for that key.
2. The session is resolved from the in-memory TTL store. The CoachAgent for that session is loaded (or created if the session is new).
3. Layer detection runs keyword and confidence heuristics on the user message and updates the session state (behaviour change layer, barriers, activities).
4. The keyword/regex router inspects the message and decides which Qdrant collection(s) to query: lesson slides, activities, or home resources.
5. The LRU cache is checked. On a hit, the cached chunks are used directly. On a miss, parallel Qdrant queries run via `ThreadPoolExecutor`, over-fetching at top_k × 2-3, then filtering on metadata (cost, location, days, type) to reach the configured top_k.
6. Retrieved chunks are truncated to 1200 characters each and assembled with current session state into a fresh system prompt for this turn.
7. GPT-4o-mini is called with `temperature=0.3`, `top_p=0.9`, `max_tokens=600`, streaming enabled.
8. Tokens stream back to the browser over SSE as they arrive.

---

## Infrastructure

### Docker
You have two services (FastAPI + Qdrant) that need to run together with shared networking and isolated environments. Docker Compose gives you a single `up` command that handles both, versus manually managing processes, ports, and dependencies on the host.

**Alternatives considered:**
- *Running directly on the host:* works but Qdrant and the API share the same OS environment with no isolation, and deployment becomes manual process management rather than `docker-compose up`.
- *Podman:* functionally similar to Docker but less tooling support, and the Lightsail instance uses standard Docker with no meaningful benefit for a single-instance setup.
- *AWS-managed containers (ECS / Fargate / App Runner):* removes the need to manage a server but adds significant cost and complexity for two containers with predictable, low traffic.
- *PaaS (Heroku / Railway / Render):* handles infra for you but Qdrant requires persistent volume storage and a self-hosted deployment, which PaaS platforms don't support cleanly without extra configuration.

### AWS Lightsail
A single fixed-price VPS is the right fit for a low-traffic app with predictable load: no surprise bills, no ECS/Kubernetes complexity. EC2 with auto-scaling or a managed container service would be overkill for one instance running two Docker containers.

### GitHub Actions
The deployment is just an SSH into Lightsail to `git pull` and `docker-compose up`, which fits naturally as a push-to-main trigger. A dedicated CD tool like CircleCI or Railway would add cost and a platform dependency for a workflow this simple.

---

## Backend

### Python 3.11
3.11 brought meaningful interpreter speed improvements over 3.10 and had broad ecosystem support when the project was built. 3.12 introduced breaking changes in some packages and was not yet the stable community default at the time.

### FastAPI
Flask is the obvious Python alternative but lacks native async support and requires third-party libraries for OpenAPI docs and request validation. FastAPI gives you async out of the box, automatic schema generation, and Pydantic validation with less boilerplate, all of which matter for a streaming SSE endpoint and a voice pipeline where latency is visible to the user.

### Uvicorn
FastAPI is an ASGI framework, so it requires an ASGI server. Gunicorn is WSGI and doesn't support async natively. Uvicorn is the standard ASGI server for FastAPI and is the recommended pairing in the official docs.

### API key auth (X-API-Key header) vs JWT/OAuth
The app has a small, controlled set of clients rather than a public sign-up flow, so API keys distributed out-of-band are simpler and sufficient. JWT and OAuth are designed for user identity at scale with token refresh flows, which adds complexity that isn't warranted here.

### slowapi for rate limiting
slowapi is the standard rate-limiting library for FastAPI and integrates directly with FastAPI's dependency injection and route decorators. Writing custom middleware to count requests per key per window would duplicate what it already does reliably.

### In-memory session store vs Redis
On a single Lightsail instance, in-memory is simpler and avoids an extra network hop. Redis only pays off with multiple instances or cross-restart session persistence, neither of which applies to this deployment.

### One CoachAgent instance per session
The agent holds mutable state specific to each user: conversation history, inferred behaviour change layer, barriers, and activities. Sharing one agent across sessions would require thread-safe per-request state isolation, which is more complex and error-prone than one isolated instance per session.

---

## AI / LLM Provider

### OpenAI as single provider
Whisper for STT and TTS are OpenAI-exclusive or best-in-class within that platform, so consolidating on one provider eliminates extra API credentials, separate SDKs, and additional billing. One key, one SDK, one bill.

### GPT-4o-mini vs GPT-4o
Coaching responses are capped at 600 tokens and heavily guided by the system prompt, so the task doesn't require the full capability ceiling of GPT-4o. Mini handles it reliably at a fraction of the cost, which matters for a consumer-facing app with ongoing inference costs.

### GPT-4o-mini vs newer models (o-series, GPT-4.1)
The o-series models are optimized for multi-step reasoning and chain-of-thought tasks: they're slower, more expensive, and expose different API parameters that don't match a streaming chat use case. GPT-4o-mini handles structured coaching responses reliably, and the task doesn't require deep reasoning, just grounded retrieval and tone control.

### Why not fine-tune
Fine-tuning teaches a model new behaviour and style, not new knowledge, so it would not reliably ground responses in the specific course content. RAG lets you update the knowledge base by editing a text file and re-running ingest, whereas fine-tuning would require curating training examples and retraining every time the content changes.

### Whisper STT vs Deepgram / Google / AWS Transcribe
OpenAI's hosted Whisper delivers strong accuracy across accents and ages for a general speech use case, and it lives in the same SDK and billing account as the chat and TTS models. Deepgram has marginally faster response times but adds a separate vendor; Google and AWS Transcribe cost more for comparable accuracy.

### OpenAI TTS vs ElevenLabs / Google / AWS Polly
OpenAI TTS is integrated in the same SDK, low-latency, and produces natural-sounding output for conversational text. ElevenLabs has more expressive emotional range but significantly higher cost and a separate integration that isn't justified for this use case.

---

## RAG Pipeline

### Qdrant
It ships as a self-contained Docker image with no external dependencies, so it fits cleanly inside the Compose stack on a single Lightsail instance. Alternatives like Pinecone or Weaviate are either cloud-only (adds cost and a network hop) or heavier to self-host.

### LlamaIndex
It handles the full ingestion pipeline (chunking, embedding, loading into Qdrant) without having to write that plumbing from scratch. Compared to LangChain, it has a tighter focus on RAG and document retrieval rather than general agent orchestration, which matches what `rag/ingest.py` actually needs.

### 3 separate Qdrant collections vs 1 with metadata filtering
Separate collections keep retrieval scoring independent: a high-scoring activity result doesn't compete with a high-scoring lesson chunk. Filtering on a single collection would dilute relevance rankings across content types with very different structures.

### Cosine distance vs dot product / Euclidean
Cosine similarity is invariant to vector magnitude, which matters when comparing embeddings of text chunks with different lengths. Dot product rewards high-magnitude vectors regardless of direction, and Euclidean distance doesn't reflect semantic angle, making cosine the standard choice for normalized text embeddings.

### Keyword/regex router vs LLM-based routing
The router runs on every message, so an LLM call just to decide which index to query would add latency and cost before the main generation step. The query space is well-defined (a fixed set of location names, activity types, and home resource keywords), so heuristics are reliable and run in microseconds.

### Over-fetch then filter strategy
Qdrant's ANN search doesn't support arbitrary post-retrieval filters, so the retriever fetches more results than needed (top_k * 2 or * 3), applies metadata filters (cost, location, days, type), then trims to the configured top_k. Fetching exactly top_k would risk returning too few usable results after filtering.

### ThreadPoolExecutor for parallel Qdrant queries
Each Qdrant query is I/O-bound (a network call plus an embedding API call), so the collections can be queried concurrently without blocking each other. Parallel execution reduces perceived latency for multi-collection queries from N * latency to roughly 1 * latency.

### In-memory LRU cache (256 entries)
Repeat queries (the same opening question from many users) skip the embedding and Qdrant round-trip entirely. 256 entries covers common patterns without unbounded memory growth on a single instance; entries are evicted in insertion order when the limit is hit.

### Deterministic chunk UUIDs
Using uuid5 seeded from the chunk ID means re-running ingest produces the same vector IDs, so Qdrant upserts are idempotent. Without this, each ingest run would create duplicate entries rather than overwriting existing ones.

### 1200 character chunk truncation
Caps the context window contribution of any single chunk to prevent one long slide from dominating the prompt. Keeps total retrieved context predictable relative to the 600 token response cap. Cuts at the last sentence boundary within the limit rather than a raw character index, so a truncated chunk never ends mid-sentence — an earlier version applied the cap to text that still included the full metadata dict, wasting 250-400 characters of the budget on data never used in the prompt; fixed by extracting metadata separately from chunk text before truncating.

### master_top_k=7 (was 5)
Raised after a RAGAS eval showed low-faithfulness responses correlating with synthesis-style questions ("why does X work") whose answer spans more slides than a hard top_k=5 ceiling could surface. No similarity-score floor was added alongside this: retrieval scores aren't currently logged or benchmarked, so picking a cutoff value without that data risked silently dropping good matches. Worth revisiting once score distributions are visible.

### Neighbor-slide stitching
A single concept's explanation is often split across two adjacent slides (one introduces a concept, the next elaborates on it), but retrieval only ever scored one slide in isolation. Each retrieved master slide now has its immediate same-lesson/same-science-module neighbor appended, so the model sees both halves instead of a fragment.

### Explicit retrieved-content delimiters + omission-over-inference grounding clause
The grounding instruction ("only state what's explicitly in the retrieved content") was previously plain-text concatenated directly above the context block with no structural boundary between instruction and data. Retrieved content is now wrapped in `<retrieved_content>...</retrieved_content>` tags so the model can distinguish where the instruction ends and the data begins. The grounding clause itself was also extended to explicitly prefer omitting a detail over inferring/generalizing when retrieved content only partially covers the question, rather than relying on the model to infer that preference.

### Plain text files as data source vs database or structured format
The content originated as course slides. Plain text is human-editable, diff-friendly in git, and trivial to re-ingest. The parsing scripts handle structure extraction at ingest time, so there's no need for a database or intermediate format.

---

## Coach Agent

### Custom CoachAgent vs LangChain
LangChain abstracts away exactly the parts that needed the most control here: response mode branching, post-processing, citation injection, and per-turn state inference. Custom code made it straightforward to add those without fighting the framework.

### Heuristic layer detection vs ML classifier
The signal vocabulary is small and well-defined: frequency phrases, goal statements, and barrier expressions. Training a classifier would require labeled conversation data that doesn't exist yet and would be harder to inspect and adjust than the current keyword and confidence rules.

### Dynamically assembled prompts vs a static system prompt
The system prompt is built fresh each turn from current session state (inferred behaviour layer, barriers, activities). This means the model always has the latest user context without needing to re-parse conversation history itself.

### temperature=0.3 / top_p=0.9
Originally 0.8, lowered after a RAGAS eval showed faithfulness violations (the model adding details not present in retrieved content) concentrated in generation, not retrieval. 0.8 was tuned for conversational variation but is high for a system meant to stay grounded in retrieved slide content. 0.3 keeps enough tone variation while reducing the odds of the model reaching past what was retrieved. top_p=0.9 unchanged: it trims the lowest-probability tokens to reduce rambling.

### max_tokens=600
Coaching responses are conversational and should be concise. A hard cap prevents runaway generation that would make responses feel like essays and degrade streaming experience on slower connections.

---

## Frontend

### No frontend framework (plain HTML/CSS/JS) vs React/Vue
The UI is a single-page chat interface with voice input and SSE streaming, which doesn't justify a build pipeline or component framework. Serving static files directly from FastAPI keeps the deployment to one container and removes an entire layer of tooling.

### Browser MediaRecorder API vs alternatives
The native browser API for audio capture with no third-party JavaScript dependency. The WebAudio API would give lower-level control but adds complexity for a straightforward record-and-send use case.

### SSE vs WebSockets
Streaming chat only requires tokens to flow one way: server to browser. WebSockets add bidirectional complexity that isn't needed here, and SSE works over standard HTTP with no extra protocol negotiation.

---

## Embeddings

### text-embedding-3-large vs text-embedding-3-small
The knowledge base is dense and topic-similar (all physical activity content), so higher-dimensional embeddings give better discrimination between lesson slides that cover related but distinct concepts. The cost difference for a one-time ingest is negligible.

### 3072 dimensions vs lower (1536 or custom)
3072 is the native output dimension of `text-embedding-3-large`, the maximum it produces without truncation. Reducing dimensions via the API's `dimensions` parameter would compress the representation and increase the chance of collisions between topically similar but distinct lesson slides across three collections.

---

## Config

### app_config.py as single source of truth vs scattered constants
All tuneable values in one file means you can adjust limits, thresholds, and timeouts without hunting through multiple modules. Environment variable overrides allow deployment-time changes without code changes, and the file itself serves as documentation of every dial in the system.
