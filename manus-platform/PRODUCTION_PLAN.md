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
- [ ] M1.1 FastAPI server with `/api/task` endpoint (accept goal, return session ID)
- [ ] M1.2 Agent loop: receive goal → generate todo.md → execute step-by-step
- [ ] M1.3 Tool framework: shell, file read/write, web fetch
- [ ] M1.4 Multi-model routing (Claude, GLM, Kimi via existing API keys)
- [ ] M1.5 WebSocket streaming of agent output (thoughts, actions, results)
- [ ] M1.6 todo.md read/update every iteration
- [ ] **Gate**: `curl -X POST /api/task -d '{"goal":"create a hello world python script"}'` → agent creates file, returns result

### Milestone 2: Docker Sandbox — TARGET: Aug 17
- [ ] M2.1 Isolated Docker container per session (Ubuntu base + Python + Node)
- [ ] M2.2 Tool execution happens inside sandbox (not host)
- [ ] M2.3 File system isolation (sandbox has its own workspace)
- [ ] M2.4 Session lifecycle: create on task start, destroy on completion/timeout
- [ ] **Gate**: Agent writes a file in sandbox → file exists in container, not on host

### Milestone 3: Web UI — TARGET: Aug 20
- [ ] M3.1 Task input screen (chat-like interface)
- [ ] M3.2 Live workspace view: terminal output streaming
- [ ] M3.3 todo.md panel (shows plan, marks completed steps)
- [ ] M3.4 File browser (view files agent creates in real-time)
- [ ] M3.5 Result display (final deliverable)
- [ ] **Gate**: Open browser → submit task → watch agent work live → see result

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

## What Does NOT Exist Yet

- ❌ Agent loop backend
- ❌ Web UI
- ❌ Docker sandbox for agent execution
- ❌ WebSocket streaming
- ❌ Authentication
- ❌ Production deployment

---

## Repository Structure (Target)

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
| M1 | `curl -X POST localhost:8000/api/task -d '{"goal":"write hello.py"}'` | Agent creates file, returns session ID |
| M2 | `docker exec <sandbox> cat /workspace/hello.py` | File exists in sandbox only |
| M3 | Open `localhost:5173` in browser | See agent working live |
| M4 | Submit multi-part research task | Sub-agents spawn, parallel results |
| M5 | Open `https://gab44.com` | Public platform, signup works |

---

## Rules for This Build

1. **No talk, only code.** Every session produces runnable code, not plans.
2. **Push after every work session.** GitHub commits = progress.
3. **Gates are mandatory.** No moving to next milestone until current gate passes.
4. **This plan is public.** Anyone can check progress at this file on GitHub.
5. **Update checkboxes.** When a task is done, check it. The checkbox state IS the status report.
