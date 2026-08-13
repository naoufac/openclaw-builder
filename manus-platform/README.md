# Manus-Like Platform

A self-hosted AI agent platform inspired by [Manus AI's architecture](../docs/manus-discipline/manus-discipline.md).

**Live**: gab44.com (coming soon)
**Status**: Active build — see [PRODUCTION_PLAN.md](./PRODUCTION_PLAN.md)

## What This Is

A platform where users submit natural-language tasks, watch an AI agent execute them in real-time (planning, tool use, file creation), and receive complete deliverables.

Built on verified Manus discipline principles:
- Single agent loop (no multi-agent consensus)
- todo.md protocol (plan read every iteration)
- File-system memory
- Frozen prefix + append-only context
- Parallel sub-agents for throughput (Wide Research)
- Failures stay in context

## Architecture

```
User → Web UI → FastAPI Backend → Agent Loop
                                  ├── todo.md protocol
                                  ├── Tool execution (shell, files, web, code)
                                  ├── File-system memory
                                  └── Parallel sub-agents (Wide Research)
                                      ↓
                              Docker Sandbox (isolated per session)
```

## Development Status

| Milestone | Target | Status |
|-----------|--------|--------|
| M1: Core Agent Loop | Aug 15 | 🔨 Building |
| M2: Docker Sandbox | Aug 17 | ⏳ Pending |
| M3: Web UI | Aug 20 | 🔨 Building |
| M4: Sub-Agents + Memory | Aug 23 | ⏳ Pending |
| M5: Auth + Deploy | Aug 27 | ⏳ Pending |

## Tech Stack

- **Backend**: Python 3.12 + FastAPI + WebSocket
- **Frontend**: React + Vite + TypeScript
- **Sandbox**: Docker (Ubuntu 24.04)
- **Models**: Multi-provider (Claude, GLM, Kimi)

## Repository

```
manus-platform/
├── backend/          # FastAPI agent server
├── frontend/         # React web UI
├── docker/           # Docker configs (sandbox + production)
├── PRODUCTION_PLAN.md  # Live progress tracker
└── README.md         # This file
```

## License

Proprietary — Gab44
