# Manus-Like Platform — Production Plan

**Goal**: Ship a self-hosted Manus-like agent platform at gab44.com
**Start date**: August 13, 2026
**Status**: ACTIVE BUILD — MVP LIVE

---

## What We're Building

A web platform where users submit tasks in natural language, watch an AI agent execute them in real-time (todo.md, terminal, file system), and receive complete deliverables. Self-hosted, multi-model, ours.

Based on our verified Manus discipline docs (`docs/manus-discipline/`).

---

## Architecture (Single Agent Loop)

```
User → Web UI → FastAPI Backend → Agent Loop
                                  ├── todo.md protocol
                                  ├── Tool execution (shell, files, web, code)
                                  ├── File-system memory
                                  └── Parallel sub-agents (Wide Research)
                                      ↓
                              Docker Sandbox
```

**Key principle**: ONE agent loop. No multi-agent consensus. No voting. Just one well-tooled loop with file memory and aggressive tool use.

---

## Milestones

### Milestone 1: Core Agent Loop (Backend) — TARGET: Aug 15
- [x] M1.1 FastAPI server with `/api/task` endpoint (accept goal, return session ID)
- [x] M1.2 Agent loop: receive goal → generate todo.md → execute step-by-step
- [x] M1.3 Tool framework: shell, file read/write, web fetch
- [x] M1.4 Multi-model routing (Claude, GLM, Kimi via existing API keys)
- [x] M1.5 WebSocket streaming of agent output (thoughts, actions, results)
- [x] M1.6 todo.md read/update every iteration
- [x] **Gate**: `curl -X POST /api/task -d '{"goal":"create a hello world python script"}'` → agent creates session, returns session_id ✓

### Milestone 2: Docker Sandbox — TARGET: Aug 17
- [x] M2.1 Isolated Docker container per session (Ubuntu base + Python + Node)
- [x] M2.2 Tool execution happens inside sandbox (not host)
- [x] M2.3 File system isolation (sandbox has its own workspace)
- [x] M2.4 Session lifecycle: create on task start, destroy on completion/timeout
- [x] **Gate**: Agent writes a file in sandbox → file exists in workspace, sandbox cleaned up after completion ✓

### Milestone 3: Web UI — TARGET: Aug 20
- [x] M3.1 Task input screen (chat-like interface)
- [x] M3.2 Live workspace view: terminal output streaming
- [x] M3.3 todo.md panel (shows plan, marks completed steps)
- [x] M3.4 File browser (view files agent creates in real-time)
- [x] M3.5 Result display (final deliverable)
- [x] **Gate**: `npx tsc --noEmit && npm run build` → passes, Docker image builds ✓

### Milestone 4: Sub-Agents + Memory — TARGET: Aug 23
- [x] M4.1 Wide Research: spawn parallel sub-agents for independent tasks
- [ ] M4.2 Cross-session file memory (tasks reference prior work) — **Deferred post-MVP**
- [x] M4.3 Failure-in-context (errors stay visible, not cleaned)
- [x] **Gate**: Submit "research 3 topics in parallel" → 3 sub-agents run, results synthesized ✓

### Milestone 5: Auth + Polish + Deploy — TARGET: Aug 27
- [x] M5.1 Temporary basic auth (Caddy-level) protecting the live URL
- [ ] M5.2 Task history dashboard — **Next polish item**
- [ ] M5.3 Rate limiting + usage tracking — **Post-MVP**
- [x] M5.4 Caddy reverse proxy config for manus.gab44.com + sslip.io fallback
- [x] M5.5 Docker Compose production deployment on Anouf server
- [x] **Gate**: Live URL works, submit task over HTTPS, agent completes in sandbox ✓

---

## Status Snapshot

| Milestone | Target | Status |
|-----------|--------|--------|
| M1: Core Agent Loop | Aug 15 | ✅ Complete + E2E verified |
| M2: Docker Sandbox | Aug 17 | ✅ Complete + E2E verified |
| M3: Web UI | Aug 20 | ✅ Scaffold complete + builds verified |
| M4: Sub-Agents + Memory | Aug 23 | ✅ Sub-agents + Wide Research complete + E2E verified |
| M5: Auth + Deploy | Aug 27 | ✅ MVP live on sslip.io, Caddy ready for manus.gab44.com |

---

## Live URLs

| URL | Status | Notes |
|-----|--------|-------|
| https://manus.135.181.44.161.sslip.io | ✅ Live now | Temporary until DNS updated |
| https://manus.gab44.com | ⏳ Awaiting DNS | Add A record → `135.181.44.161` |

**Basic auth credentials (temporary):** `nao` / `manus2026`

---

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Backend | Python 3.12 + FastAPI | Async, WebSocket support, fast |
| Agent loop | Custom (following Manus discipline) | No framework gives us the control we need |
| Sandbox | Docker (Ubuntu 24.04 base) | Isolation, reproducibility |
| Frontend | React + Vite + TypeScript | Fast, we know it, real-time friendly |
| Streaming | WebSocket (server→client) | Live agent output |
| Models | Multi-provider (Zai, Kimi, OpenAI, Mistral) | Dynamic routing, cost optimization |
| Database | SQLite (dev) → PostgreSQL (prod) | Simple start, scale when needed |
| Deploy | Docker Compose + Caddy on Anouf server | We already have the infrastructure |

---

## What Exists Already

- ✅ Manus discipline docs (verified architecture, 10 binding rules)
- ✅ Server infrastructure (Anouf: 8 cores, 15GB RAM, Docker, Caddy)
- ✅ gab44.com domain (subdomains point to server; apex currently points elsewhere)
- ✅ Multi-model API keys (wired from OpenClaw host config)
- ✅ This repository
- ✅ M1 backend: FastAPI agent loop + tools + WebSocket + multi-model routing
- ✅ M2 sandbox: per-session Docker container, auto-cleanup
- ✅ M3 frontend: React UI + live workspace + todo/terminal/file panels
- ✅ M4 sub-agents: parallel spawn + wide_research + depth limiting
- ✅ M5 deploy: live HTTPS with Caddy + Docker Compose

## What Does NOT Exist Yet

- ❌ M4.2 Cross-session file memory (deferred post-MVP)
- ❌ App-level user authentication (login/signup) — temporary Caddy basic auth in place
- ❌ Task history dashboard
- ❌ Rate limiting + usage tracking
- ❌ manus.gab44.com DNS A record updated

---

## Repository Structure

```
manus-platform/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── agent/
│   │   ├── loop.py          # Core single agent loop
│   │   ├── todo.py          # todo.md protocol (read/update every iteration)
│   │   ├── context.py       # Frozen prefix + append-only working area
│   │   └── subagent.py      # Wide Research parallel spawning
│   ├── tools/
│   │   ├── shell.py         # Shell command execution (inside sandbox)
│   │   ├── files.py         # File read/write/list
│   │   ├── web.py           # Web fetch + search
│   │   ├── code.py          # Python code execution in sandbox
│   │   └── subagent.py      # spawn_subagent / wide_research tool wrappers
│   ├── sandbox/
│   │   ├── __init__.py
│   │   ├── manager.py       # Docker container lifecycle
│   │   └── Dockerfile       # Base sandbox image
│   ├── models/
│   │   └── router.py        # Multi-model routing
│   ├── ws/
│   │   └── stream.py        # WebSocket event streaming
│   ├── tests/
│   │   ├── test_sandbox.py  # 13 sandbox lifecycle tests
│   │   └── test_subagent.py # 17 sub-agent tests
│   ├── pytest.ini
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── TaskInput.tsx
│   │   │   ├── AgentView.tsx        # Live workspace (terminal + todo + files)
│   │   │   ├── TodoPanel.tsx        # todo.md display with progress
│   │   │   ├── TerminalPanel.tsx    # Streaming agent output
│   │   │   ├── FileBrowser.tsx      # Files created by agent
│   │   │   └── ResultView.tsx       # Final deliverable
│   │   └── hooks/
│   │       └── useAgentStream.ts    # WebSocket hook
│   ├── package.json
│   ├── vite.config.ts
│   ├── nginx.conf
│   └── Dockerfile
├── docker/
│   ├── docker-compose.yml           # Production compose
│   └── sandbox/
│       └── Dockerfile               # Base sandbox image (also used by backend)
├── docs/
│   └── Caddyfile                    # Caddy reverse proxy config
├── PRODUCTION_PLAN.md               # This file
└── README.md
```

---

## Verification Gates (No Exceptions)

| Milestone | Gate Command | Expected |
|-----------|-------------|----------|
| M1 | `curl -X POST localhost:8000/api/task -d '{"goal":"write hello.py"}'` | ✅ Returns session_id, backend active |
| M2 | `docker exec <sandbox> cat /workspace/hello.py` | ✅ File exists in sandbox only, container removed after completion |
| M3 | `npx tsc --noEmit && npm run build` | ✅ TypeScript passes, production build succeeds |
| M4 | `wide_research` spawns 3 parallel sub-agents | ✅ 3+ child sandboxes created, results synthesized |
| M5 | `curl -u nao:manus2026 https://manus.135.181.44.161.sslip.io/api/health` | ✅ Returns `{"status":"ok"}`, task submission completes over HTTPS |

---

## Rules for This Build

1. **No talk, only code.** Every session produces runnable code, not plans.
2. **Push after every work session.** GitHub commits = progress.
3. **Gates are mandatory.** No moving to next milestone until current gate passes.
4. **This plan is public.** Anyone can check progress at this file on GitHub.
5. **Update checkboxes.** When a task is done, check it. The checkbox state IS the status report.
