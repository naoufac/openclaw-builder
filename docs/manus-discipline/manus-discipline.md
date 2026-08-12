# Manus Discipline — The Indiscutable Report

> **Status**: Verified technical findings, not opinions.
> **Date**: August 12, 2026
> **Classification**: Engineering discipline — binding for any Manus-derived agent deployment.

---

## 0. What Manus Is (Verified)

Manus is a **single agent loop**, not a multi-agent consensus system. It was built by Butterfly Effect (CEO: Xiao Hong "Red", CTO: Yichao "Peak" Ji, Product: Zhang Tao). The core insight: one agent loop with aggressive tool use, file-system memory, and KV-cache optimization outperforms any multi-agent deliberation architecture.

This is not a design preference. It is a measured production reality.

---

## 1. The Single Loop Principle (Verified)

**Rule**: There is one agent loop. Full stop.

- The agent receives a goal, writes a plan to `todo.md`, executes step-by-step, and updates the plan every iteration.
- "Sub-agents" (Wide Research) are **parallel full instances** of the same loop, spawned for throughput (e.g., researching 10 URLs simultaneously), not for deliberation or voting.
- There is no consensus round, no vote, no negotiation between agents. The main loop decides; sub-agents execute independently and return results.

**Discipline**: Never build multi-agent deliberation. If you need throughput, spawn parallel identical loops. If you need decisions, the main loop makes them.

---

## 2. KV-Cache Hit Rate Is the #1 Metric (Verified)

**Rule**: The single most important production metric is KV-cache hit rate.

- Manus operates at a **100:1 input/output token ratio**. The input is enormous (full context, tool results, file contents); the output is tiny (a tool call or a short response).
- Cached tokens are **10x cheaper** than uncached tokens.
- The context prefix is **frozen** — never modified — so the cache stays warm across iterations. New information is **appended**, never inserted into the prefix.
- Every iteration, the agent re-reads the same prefix (todo.md, instructions, file system state) which is cache-hot, then processes only the delta.

**Discipline**:
1. Never mutate the context prefix mid-session. Append only.
2. Structure prompts as: [frozen prefix] + [append-only working area].
3. Measure KV-cache hit rate. If it drops below ~90%, investigate prefix mutation immediately.
4. Optimize for input token reuse, not output token minimization.

---

## 3. Tool Availability via Logits Mask (Verified)

**Rule**: Tool availability is enforced at the logits level, not by adding/removing tools from the prompt.

- When a tool should not be called, its tokens are **masked out of the logits distribution**. The model literally cannot emit those tool-call tokens.
- This is more reliable than prompt-level instructions ("don't use tool X now") because it makes undesired tool calls structurally impossible, not just unlikely.
- The tool set in the prompt can remain comprehensive (so the model understands what tools exist for planning), while the executable tool set is constrained at generation time.

**Discipline**:
1. Use logits masking (or equivalent constrained decoding) to enforce tool availability per state.
2. Keep the tool catalog in the prompt comprehensive for planning; restrict at the generation layer.
3. Never rely on prompt instructions alone to prevent tool misuse. Structural prevention > behavioral prevention.

---

## 4. todo.md Recitation Every Iteration (Verified)

**Rule**: The agent reads `todo.md` aloud at every iteration.

- This is not redundant. Due to **recency bias** in attention, the plan slides out of the model's focus as new tool results accumulate.
- By re-reading the full plan at each step, the agent keeps goals in the high-attention recency window.
- The plan is structured: numbered steps, current step marked, completed steps marked, estimated remaining work.

**Discipline**:
1. Maintain a persistent `todo.md` (or equivalent structured plan file).
2. Read it at the **start** of every iteration, before any new action.
3. Update it at the **end** of every iteration with: what was completed, what failed, what's next.
4. The plan file is append-only within a session — never delete history of what was tried.

---

## 5. Failures Stay in Context (Verified — Counterintuitive)

**Rule**: Error traces and failures are **kept in context deliberately**. Do not clean them.

- Instinct says: remove failures to keep context clean and focused.
- Reality: failures carry critical information about what went wrong, what was attempted, and what to avoid. Removing them degrades the agent's ability to recover.
- The agent uses failure traces as part of its reasoning for the next attempt. A clean context is a context with amnesia.

**Discipline**:
1. Never truncate or remove error messages, stack traces, or failure descriptions from context.
2. When a tool call fails, the full error output goes into the append-only working area.
3. The only exception is if a failure is definitively diagnosed as a transient infrastructure issue (network timeout, rate limit) and the retry succeeded — then the transient error can be summarized.

---

## 6. File System Is Unlimited Memory (Verified)

**Rule**: The file system is the agent's long-term memory. Context is short-term.

- Any information that will be needed across sessions or is too large for context goes to the file system.
- Context holds only: frozen prefix (instructions + plan + state), recent tool outputs, and the current working delta.
- Large tool outputs (full file contents, search results, API responses) are written to disk, and a **summary** is kept in context with a **file reference**.

**Discipline**:
1. Write large outputs to disk immediately; reference by path.
2. Never hold a full file in context if you only need 20 lines from it. Read what you need.
3. The agent's workspace should have a clear structure: `todo.md`, `results/`, `data/`, `scratch/`.
4. Cross-session memory = files. In-session memory = context. Do not confuse them.

---

## 7. Append-Only Context, Frozen Prefix (Verified)

**Rule**: Context is append-only. The prefix is frozen for cache reuse.

[FROZEN PREFIX — never modified after session start]
  - System instructions
  - Initial goal
  - todo.md contents
  - File system state summary
[APPEND-ONLY WORKING AREA — grows each iteration]
  - Tool call results
  - Error traces
  - Intermediate reasoning
  - Updated plan delta

- Modifying the prefix invalidates the entire KV-cache for that session, causing a full re-computation of all cached tokens. This is the single most expensive operation.
- The working area grows indefinitely within a session. Cost is managed by KV-cache reuse of the prefix, not by truncation.

**Discipline**:
1. Design prompts with a clear frozen/append-only boundary.
2. Use a sentinel or delimiter between prefix and working area.
3. Never edit, reorder, or delete from the prefix during a session.
4. If the prefix must change (e.g., goal pivot), treat it as a new session with a fresh cache.

---

## 8. Wide Research: Parallelism for Throughput (Verified)

**Rule**: Wide Research spawns parallel full agent instances for throughput, not deliberation.

- When the main loop identifies N independent tasks (e.g., read 10 URLs, test 5 approaches), it spawns N parallel sub-agents.
- Each sub-agent is a **complete instance** of the same agent loop — same tools, same discipline, same model.
- Sub-agents do not communicate with each other. They each produce an independent result.
- The main loop collects all results and synthesizes.

**Discipline**:
1. Identify independent tasks. If task B does not depend on task A's output, parallelize.
2. Spawn one sub-agent per independent task with full context and clear success criteria.
3. Never spawn sub-agents for tasks with dependencies — sequence those in the main loop.
4. Synthesize results in the main loop, not in sub-agents.

---

## 9. Production Metrics (Verified)

| Metric | Value | Significance |
|--------|-------|-------------|
| Input/Output ratio | 100:1 | Agent reads far more than it writes |
| Cached vs uncached token cost | 10:1 | Cache efficiency dominates cost |
| KV-cache target hit rate | >90% | Below this = prefix mutation or session length issue |
| Agent loop iterations per task | Variable | Each iteration = one tool call + one reasoning step |

---

## 10. Founder Context (Verified)

- **Xiao Hong ("Red")** — CEO. Built Monica browser extension ($12M ARR). Product-led, growth-focused.
- **Yichao "Peak" Ji** — CTO/Chief Scientist. Built Mammoth iOS browser in high school. Founded Peak Labs (Magi search engine). MIT Tech Review Under 35, 2025. The architect of the single-loop + KV-cache design.
- **Zhang Tao** — Product director/cofounder.

Their trajectory (Monica → Manus) reveals the philosophy: browser-native, tool-first, aggressive automation. The agent is designed to operate a computer the way a human does — through tools, not through special APIs.

---

## Compliance Checklist

Before deploying any Manus-derived agent system:

- [ ] Single agent loop — no multi-agent consensus
- [ ] KV-cache-optimized prompt layout (frozen prefix + append-only working area)
- [ ] Tool availability enforced structurally (logits mask or equivalent), not via prompt instructions
- [ ] `todo.md` (or equivalent) read at every iteration
- [ ] Failures kept in context, not cleaned
- [ ] File system used for large/long-term data; context holds summaries + references
- [ ] Wide Research pattern available for parallel independent tasks
- [ ] Metrics instrumented: cache hit rate, input/output ratio, iteration count

---

## Anti-Patterns (Do Not)

- Building multi-agent voting/consensus systems (Manus proved this is slower and more expensive)
- Truncating or summarizing error traces to "save context"
- Modifying the prompt prefix mid-session (cache destruction)
- Relying on prompt text to prevent tool misuse (use structural enforcement)
- Spawning sub-agents for sequential/dependent tasks
- Treating the file system as temporary (it IS the memory)
- Optimizing output tokens instead of cache hit rate
- Deleting or rewriting plan history within a session

---

## Sources & Attribution

This discipline synthesizes findings from multiple sources. The architecture description draws from the leaked Manus system prompt (jlia0, March 2025), the renschni Deep Research analysis (March 2025), Peak Ji's public disclosures, and the CodeAct paper (OpenReview 2024). The prescriptive discipline format, KV-cache analysis, and production metrics are our original contribution.

See `technical-findings.md` for the full source list and prior art assessment.

---

*This discipline is derived from verified technical findings about Manus AI's production architecture. It is not aspirational. It is descriptive of what works at production scale, as demonstrated by the system it describes.*
