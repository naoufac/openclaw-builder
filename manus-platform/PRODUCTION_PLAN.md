# Manus-Like Platform — Production Plan

**Goal**: Ship a self-hosted Manus-like agent platform at gab44.com
**Start date**: August 13, 2026
**Status**: ACTIVE BUILD

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
- [x] M2.1 Isolated Docker container per session (Ubuntu base + Python + Node) — base image built
- [ ] M2.2 Tool execution happens inside sandbox (not host)
- [ ] M2.3 File system isolation (sandbox has its own workspace)
- [ ] M2.4 Session lifecycle: create on task start, destroy on completion/timeout
- [ ] **Gate**: Agent writes a file in sandbox → file exists in container, not on host

### Milestone 3: Web UI — TARGET: Aug 20
- [x] M3.1 Task input screen (chat-like interface)
- [x] M3.2 Live workspace view: terminal output streaming
- [x] M3.3 todo.md panel (shows plan, marks completed steps)
- [x] M3.4 File browser (view files agent creates in real-time)
- [x] M3.5 Result display (final deliverable)
- [x] **Gate**: Open `localhost:5173` in browser → UI renders, TypeScript passes, Docker image builds ✓

### Milestone 4: Sub-Agents + Memory — TARGET: Aug 23
- [ ] M4.1 Wide Research: spawn parallel sub-agents for independent tasks
- [ ] M4.2 Cross-session file memory (tasks reference prior work)
- [ ] M4.3 Failure-in-context (errors stay visible, not cleaned)
- [ ] **Gate**: Submit "research 3 topics in parallel" → 3 sub-agents run, results synthesized

### Milestone 5: Auth + Polish + Deploy — TARGET: Aug 27
- [ ] M5.1 User authentication (signup/login, session isolation)
- [ ] M5.2 Task history dashboard
- [ ] M5.3 Rate limiting + usage tracking
- [ ] M5.4 Caddy reverse proxy config for gab44.com
- [ ] M5.5 Docker Compose production deployment
- [ ] **Gate**: gab44.com live, public user can sign up, submit task, watch execution, get result

---

## Status Snapshot

| Milestone | Target | Status |
|-----------|--------|--------|
| M1: Core Agent Loop | Aug 15 | ✅ Code complete + smoke tested |
| M2: Docker Sandbox | Aug 17 | 🔨 Base image ready, per-session integration next |
| M3: Web UI | Aug 20 | ✅ Scaffold complete + builds + Docker image builds |
| M4: Sub-Agents + Memory | Aug 23 | ⏳ Pending |
| M5: Auth + Deploy | Aug 27 | ⏳ Pending |

---

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Backend | Python 3.12 + FastAPI | Async, WebSocket support, fast |
| Agent loop | Custom (following Manus discipline) | No framework gives us the control we need |
| Sandbox | Docker (Ubuntu 24.04 base) | Isolation, reproducibility |
| Frontend | React + Vite + TypeScript | Fast, we know it, real-time friendly |
| Streaming | WebSocket (server→client) | Live agent output |
| Models | Multi-provider (Claude, GLM, Kimi) | Dynamic routing, cost optimization |
| Database | SQLite (dev) → PostgreSQL (prod) | Simple start, scale when needed |
| Deploy | Docker Compose on Anouf server | We already have the infrastructure |

---

## What Exists Already

- ✅ Manus discipline docs (verified architecture, 10 binding rules)
- ✅ Server infrastructure (Anouf: 8 cores, 15GB RAM, Docker, Caddy)
- ✅ gab44.com domain (needs Caddy config)
- ✅ Multi-model API keys (Claude, GLM, Kimi, Mistral)
- ✅ This repository
- ✅ M1 backend: FastAPI agent loop + tools + WebSocket + multi-model routing
- ✅ M3 frontend: React UI + live workspace + todo/terminal/file panels
- ✅ Docker images for backend and frontend build successfully
- ✅ Backend smoke test: `/api/health` and `/api/task` respond correctly

## What Does NOT Exist Yet

- ❌ Docker sandbox integration (tools run in container, not host)
- ❌ Sub-agent spawning (Wide Research pattern)
- ❌ Cross-session memory / database
- ❌ Authentication
- ❌ Production deployment on gab44.com

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
│   │   ├── shell.py         # Shell command execution
│   │   ├── files.py         # File read/write/list
│   │   ├── web.py           # Web fetch + search
│   │   └── code.py          # Python code execution in sandbox
│   ├── sandbox/
│   │   └── manager.py       # Docker container lifecycle
│   ├── models/
│   │   └── router.py        # Multi-model routing
│   ├── ws/
│   │   └── stream.py        # WebSocket event streaming
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
│   ├── docker-compose.yml
│   └── sandbox/
│       └── Dockerfile               # Base sandbox image
├── PRODUCTION_PLAN.md               # This file
└── README.md
```

---

## Verification Gates (No Exceptions)

Every milestone has a gate. No milestone is "done" until the gate passes and output is shown.

| Milestone | Gate Command | Expected |
|-----------|-------------|----------|
| M1 | `curl -X POST localhost:8000/api/task -d '{"goal":"write hello.py"}'` | ✅ Returns session_id, backend active |
| M2 | `docker exec <sandbox> cat /workspace/hello.py` | File exists in sandbox only |
| M3 | `npx tsc --noEmit && npm run build` | ✅ TypeScript passes, production build succeeds |
| M4 | Submit multi-part research task | Sub-agents spawn, parallel results |
| M5 | Open `https://gab44.com` | Public platform, signup works |

---

## Rules for This Build

1. **No talk, only code.** Every session produces runnable code, not plans.
2. **Push after every work session.** GitHub commits = progress.
3. **Gates are mandatory.** No moving to next milestone until current gate passes.
4. **This plan is public.** Anyone can check progress at this file on GitHub.
5. **Update checkboxes.** When a task is done, check it. The checkbox state IS the status report.
