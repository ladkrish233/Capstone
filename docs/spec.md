# Friend: product and build spec (v12)

A voice-first personal friend and assistant that remembers you, checks in on you, calls you when something matters, and does background work while it keeps talking. Open source, self-hostable, bring your own model and voice keys.

This spec replaces the build plan `personal-agent-plan-v11.md`. It keeps every decision from v11 that still holds, reorganises the plan as a product spec, and adds what we learned from studying how OpenClaw is built and developed (section 2).

| | |
|---|---|
| Status | Draft for review, 25 Nov 2026 |
| Owner | Krishna |
| Repo | `ladkrish233/Capstone` |
| Replaces | Plan v11 (kept as history; section numbers below are new) |
| How to use it | Section 12 is the build order. Section 13 lists the decisions to make before building. Every feature in section 6 has a "Done when" check |

---

## Contents

1. Summary
2. What we learned from OpenClaw
3. Product: who it is for and why it wins
4. Principles
5. Architecture
6. Features and requirements
7. Memory
8. Automations: reminders, check-ins and proactive calls
9. Voice and telephony
10. Self-improvement and evals
11. Safety, privacy and security
12. Roadmap and build order
13. Decisions to make
14. Development process (copied from OpenClaw, adapted)
15. Launch plan
16. Repository layout and data model
17. Risks
18. Appendix: what changed from v11, current code, sources

---

## 1. Summary

**What:** "Friend" (working name, see D10) is an AI friend plus personal assistant that you talk to by voice or text. It remembers your routines and preferences, checks in on meals, gym, sleep and mood, reminds you of what matters by actually calling you, hands slow work (email, calendar, web, notes) to background helpers while the conversation continues, and gets better from your feedback with your approval.

**For whom:** first for Krishna (daily use is the test), then for anyone who installs it on their own machine or server with their own API keys, the way people install OpenClaw. A hosted version is optional and later.

**Stack in one line:** Python 3.13, Pydantic AI v2 + Pydantic AI Harness (agent runtime), Pipecat (voice pipeline), FastAPI (core service and API), Postgres + pgvector (state and search), a web PWA and Streamlit (owner dashboard), Docker Compose (install), Logfire (tracing), Harness² (offline tuning).

**The big change from v11:** v11 was a single-user capstone built in course order. v12 keeps the course as the learning path, but shapes the code as a product other people can install: one core service (the "Gateway"), provider plugins with bring-your-own keys, workspace files for persona and memory, one automation system for everything proactive, an onboarding wizard and a `doctor` command, and an OpenClaw-style development and release process.

---

## 2. What we learned from OpenClaw

Studied on 25 Nov 2026 from the `openclaw/openclaw` repository (latest commit that day, version `2026.11.10`), its docs, the last 2,000 commits, and interviews with its creator. Clawd's "birthday" is 25 Nov 2025, so OpenClaw is exactly one year old today.

### 2.1 Its stack

| Layer | OpenClaw | Our equivalent |
|---|---|---|
| Language | TypeScript on Node 24+, ESM. VISION.md: chosen because it is "widely known, fast to iterate in, and easy to read, modify, and extend" | Python 3.13. Same reasoning applies: Pydantic AI and Pipecat are Python, and you already know it |
| Repo shape | pnpm monorepo: `src/` (core), `packages/` (~25 internal libraries such as `agent-core`, `gateway-protocol`, `plugin-sdk`), `extensions/` (189 plugins), `apps/` (native macOS, iOS, Android, Linux), `crates/` (Rust), `skills/` (52 bundled skills), `docs/` | One Python repo with a uv workspace: `app/` core, `plugins/` providers and channels, `services/` speech and embeddings, `skills/`, `docs/` (section 16) |
| Core process | One long-running **Gateway** daemon per host. It owns every session, channel connection, tool, event and schedule. Clients (CLI, web Control UI, TUI, apps) and devices ("nodes") connect over a typed WebSocket API on `127.0.0.1:18789`, JSON Schema validated, with idempotency keys on side-effecting calls | Our FastAPI app becomes the Gateway: one process that owns sessions, the scheduler, channels and the agent. Web, phone, Telegram and CLI are clients |
| Agent loop | Its own `agent-core` package (agent loop, tools, validation). Model providers are plugins (Anthropic, OpenAI, Google, OpenRouter, Ollama, DeepSeek, Groq and many more). Whole agent harnesses (Claude, Codex) are also swappable plugins | Pydantic AI v2 is our agent loop; Pydantic AI Harness supplies the capabilities (subagents, memory, skills, guardrails, spend limits). Providers are config, keys are the user's |
| Channels | WhatsApp (Baileys), Telegram (grammY), Slack, Discord, Signal, iMessage, Teams and 20+ more, each a plugin. Unknown senders must be paired and approved | Web PWA and phone first, then Telegram, then WhatsApp. Same pairing rule for unknown senders |
| Memory | Plain Markdown files in a workspace folder: `USER.md` (profile as directives), `MEMORY.md` (curated long-term facts), `memory/YYYY-MM-DD.md` (daily notes, searchable), `DREAMS.md` (nightly "dreaming" that distils daily notes into `MEMORY.md`). Memory is a plugin slot, only one active. Files have provenance; untrusted edits are quarantined | Same idea, Python version (section 7). It also matches Harness²'s editable surface, which wants files |
| Persona and rules | Workspace bootstrap files: `SOUL.md`, `IDENTITY.md`, `USER.md`, `AGENTS.md`, `TOOLS.md`, `BOOT.md` | `SOUL.md` replaces `prompts/friend_vN.md`; see section 7 |
| Proactive work | Originally a "heartbeat" monitor plus `HEARTBEAT.md`. They retired it: heartbeats are now ordinary **automation (cron) jobs**, each with its own schedule, prompt, scratch, model, session, delivery and run history | We skip the mistake: reminders, check-ins, digests and watchers are all one automation system from day one (section 8) |
| Voice | **Voice Call plugin**: Twilio, Telnyx, Plivo and a mock provider; inbound and outbound; `notify` or `conversation` mode; per-phone sessions so the caller is remembered; a **call brief** (task, context, language, identity, disclosures, approvals, voicemail message, success criteria, max duration); voicemail; call reports. **Talk mode** on apps and browser, including realtime speech-to-speech where the realtime voice "consults" the main agent for real work | Pipecat cascaded pipeline as the default, realtime as an option. We copy the call brief schema and the notify/conversation split (sections 8, 9) |
| Skills and tools | `SKILL.md` folders; a public registry (ClawHub); MCP as both client and server; browser control; sandboxing for tools | Pydantic AI Harness Skills; our `memory-mcp` and `notes-mcp` servers |
| State | SQLite for state and caches (their rule: no new JSON sidecar stores) | Postgres (already in Compose). See D5 |
| Setup | One-line installer, `openclaw onboard` wizard (verifies model access, creates the workspace, installs the daemon), `openclaw doctor --fix` repairs and migrates old config | `friend onboard` and `friend doctor` (section 6, F1) |
| Quality tooling | Vitest, oxlint, oxfmt, tsdown, CodeQL, Semgrep, gitleaks, ~150 GitHub workflows, live tests behind a flag, mock providers for every external service | ruff, pytest, gitleaks (already in CI), plus eval runs and mock providers |
| Licence and money | MIT. Stewarded by a non-profit foundation; no paid tier, no hosted service | See D9 |

### 2.2 How it was built

**Origin.** It started as a one-hour hack called "WhatsApp relay": Baileys linked Peter Steinberger's WhatsApp, and each incoming message ran the Claude CLI. It grew by use, not by plan: images, then voice notes (the agent worked out ffmpeg plus Whisper by itself when he sent one), then Gmail, Calendar and contacts. Names: Warelay, Clawdbot, Moltbot, OpenClaw.

**AI-written code.** The creator says every line was generated or rewritten by Codex. He runs 5 to 10 agents in parallel on separate features, spends a long time refining a plan with an agent before any code, treats pull requests as "prompt requests", and reads only security-sensitive or data-critical code closely. The system is designed so agents can verify their own work: build, lint, run tests and live checks locally instead of waiting for remote CI.

**Today's pace (from `git log`, 19 to 25 Nov 2026).** About 280 commits a day, 2,000 in a week. 63% are `fix:`, 11% `test:`, 8% `refactor:`, 5% `feat:`. Nearly every commit is a squash-merged PR (`(#205398)`). Bots are among the top committers (RoboClaw, Tideclaw Bot, openclaw-mantis). Releases use calendar versions (`2026.11.10`): 148 releases between January and November 2026, about three a week, with the changelog generated from merged PRs at release time.

**Rules that make that pace safe.** These are the parts worth copying:

1. `VISION.md` with priorities in order (security and safe defaults first) and an explicit "what we will not merge" list.
2. `AGENTS.md` at the root, kept under 20,000 characters because the agent loads it whole. It sets design priorities ("one owner per responsibility", "small core, capable plugins"), execution discipline ("reproduce the bug end to end before editing"), and points to longer guides instead of repeating them.
3. Repo-local agent skills (`.agents/skills/`, 56 of them): how to test, review a PR, cut a release, triage security.
4. Issue first for any non-trivial or agent-written work; one PR per topic; PRs over ~5,000 changed lines are not reviewed.
5. A PR template that starts with "What problem this solves", "User impact" and "Evidence" written for a user, not for the code. Titles say what changes for the person (`fix: keep automations running when you open another chat`), not the implementation.
6. Small core, everything optional as a plugin. "Each core tool, prompt line and config key reaches every operator on every model request", so the core has the strictest bar.
7. Config changes that break old config ship a `doctor` migration in the same PR.
8. Mock providers for every external service, plus live tests that run only with real keys.
9. Errors must say what went wrong and what to do next.

### 2.3 What we copy, adapt, or skip

| OpenClaw practice | Verdict for us | Why |
|---|---|---|
| Gateway as the single owner of state, sessions and schedules | **Copy** | Fixes our biggest structural gap: today `/chat`, `/voice` and reminders are separate routes with no shared session or scheduler owner |
| Providers as plugins, bring your own keys, onboarding wizard, `doctor` | **Copy** | This is what makes it installable by other people |
| Markdown workspace for persona and memory | **Copy** | Readable, editable, diffable, and exactly what Harness² tunes |
| Heartbeat folded into automations | **Copy from the start** | One scheduler, one run history, one delivery path |
| Call brief schema, notify vs conversation calls, per-phone sessions, mock telephony provider | **Copy** | Saves design work for sections 8 and 9 |
| Realtime voice with "consult the agent" | **Adapt** as an option | Better latency; our cascaded pipeline stays the default for tool reliability and Hindi support |
| AGENTS.md, VISION.md, issue-first, PR template, CalVer releases, generated changelog | **Copy, small** | You already track one issue per module; this makes it consistent |
| "Don't read the code, review the prompts" | **Skip** | Your goal is to understand every line. Claude writes, you read every diff and explain it in the PR body (section 14) |
| 5-10 parallel agents, 280 commits a day | **Skip for now** | One person learning; one or two agents on separate branches at most |
| 189 plugins, native apps, 25 channels | **Skip** | Phone, web and Telegram first. Breadth is not our edge |
| TypeScript | **Skip** | Python is right for our libraries |

### 2.4 The honest competitive point

OpenClaw can already place and receive phone calls (Voice Call plugin), run errands by phone with a brief, and run scheduled jobs. Several small apps also "call you with reminders". So "an AI that calls you" is not a moat by itself. Our edge has to come from section 3.3.

---

## 3. Product: who it is for and why it wins

### 3.1 Users

| User | Need | First version serves them? |
|---|---|---|
| Krishna (owner) | Daily friend, reminders that are not ignored, check-ins, email triage, notes search | Yes, the main test |
| Self-hosters (OpenClaw-style users) | A voice-first assistant they run with their own keys | Yes from v0.1 |
| Indian students and young professionals | Hindi/Hinglish voice, WhatsApp and phone, cheap | Partly (voice and phone in India need D4) |
| Family members (parents living alone) | A daily call with consent | Later (section 6, F14) |

### 3.2 Problems it solves

The 28 everyday problems from v11 section 23 still stand (missed meetings, ignored notifications, forgotten medication, meals, gym, bills, free trials, buried email, loneliness, phone-call anxiety and so on). They map onto five product capabilities: **calls that matter, check-ins, background helpers, memory, and knowledge collection.** The v11 design rules also stand: one saved number, no payments or OTPs, calls only for what matters, confirm-to-close, forwarding not snooping, consent for other people.

### 3.3 Why it wins (differentiators)

Ranked by how hard they are for others to copy and how much users feel them.

| # | Differentiator | What the user experiences | Others today |
|---|---|---|---|
| 1 | **Voice-first friend that calls you, with an escalation ladder** | Message first, call if no reply, retry once, then text; reminders stay open until you say "done" | Reminder apps call but do not remember you; OpenClaw is chat-first |
| 2 | **Keeps talking while it works** | "Check my email and calendar" mid-call: it keeps chatting and weaves results in when they land | Most voice agents go silent during tool calls |
| 3 | **India-first voice** | Hindi, Hinglish and Indian English in and out; WhatsApp and Indian phone numbers | Most voice agents are English and US-telephony first |
| 4 | **Memory you can read and edit** | `USER.md` and `MEMORY.md` you can open; "forget that" works; "what do you know about me?" is honest | Hidden memory in most apps |
| 5 | **Gets better, visibly, with your approval** | A weekly "here's what I learned" with diffs you approve; one-click rollback | Few products show or gate self-improvement |
| 6 | **Bring your own everything** | Any LLM, STT, TTS, telephony provider; local models for free; your data on your machine | Hosted assistants lock the stack |

**"Crazy" features worth building, in order of value** (each is a feature in section 6):

1. Morning brief call: your day, the one email that matters, the weather, in 60 seconds.
2. Escalation ladder with confirm-to-close for meetings, medication, bills and free trials.
3. Leave-by calls using travel time ("leave in 10 minutes for the 4pm").
4. Live background helpers during a call, with "what's it doing?" and "cancel that".
5. Errand calls: it calls a business for you with a brief and limits you approved (OpenClaw-style brief).
6. Rehearsal mode: practise a hard call (interview, landlord, English practice) before making it.
7. Reel and YouTube collector to notes, with a weekend digest call.
8. "Remember this" from any channel: forward a WhatsApp message or a photo of a bill, and it becomes a reminder.
9. Commute call and wind-down call.
10. Phone as a remote control for a coding agent (later, D12): "fix the failing test in Capstone and open a PR", reported back by voice.

---

## 4. Principles

1. **The talking agent never blocks on slow work.** Slow work runs in the background and reports through events.
2. **One owner per responsibility.** The Gateway owns sessions, schedules and delivery. Nothing else writes reminders or starts calls.
3. **Small core, plugins at the edges.** Every line in the friend's always-on prompt costs latency on every turn. New providers and channels are plugins, not core changes.
4. **Safety is enforced in code, not only in prompts.** Confirmations, call caps, quiet hours and permissions live in code and in `config/`, outside anything a model or the tuner can edit.
5. **Content is data.** Email, web pages, notes, reels and forwarded messages never give instructions.
6. **Reminders live in the database,** never in model memory, with dedupe keys and restart safety.
7. **Errors say what happened and what to do next.**
8. **Bring your own keys; your data stays where you run it.** No telemetry without opt-in.
9. **You understand every line.** Claude writes code; you read it, run it and can explain it.

---

## 5. Architecture

### 5.1 Target picture

```
                 Clients and channels (all are clients of the Gateway)
   Web PWA      Phone (provider     Telegram     CLI / TUI      Streamlit
   (voice+text)  webhook + media)   (later WA)   (friend ...)   (owner dashboard)
        │              │               │             │               │
        └──────────────┴───────┬───────┴─────────────┴───────────────┘
                               ▼  HTTP + WebSocket API (typed, API key / paired device)
┌──────────────────────────────────────────────────────────────────────────┐
│ GATEWAY (FastAPI, one long-running process)                               │
│                                                                           │
│  Sessions ── one per channel+person; history in Postgres                  │
│  Friend agent (Pydantic AI + Harness capabilities, fast model)            │
│     tools: spawn_subagent, recall, remember, set_reminder, log_behavior,  │
│            request_call, end_call ...                                     │
│  Subagent runner (Harness Subagents / Background Tools, strong model)     │
│  Automations ── one scheduler: reminders, check-ins, briefs, watchers     │
│  Delivery ── message → call → retry → text (escalation ladder)            │
│  Providers ── LLM, STT, TTS, telephony, embeddings: plugins + user keys   │
│  Workspace ── SOUL.md, USER.md, MEMORY.md, memory/YYYY-MM-DD.md, skills/  │
└──────────┬───────────────────────────┬───────────────────────────────────┘
           ▼                           ▼
   Voice worker (Pipecat)        Postgres + pgvector
   STT → friend → TTS,           sessions, reminders, automations, events,
   barge-in, phone serializers   audit log, cost, note chunks, embeddings

Offline, separate container: evals + Harness² tuner → proposed harness versions → your approval
```

### 5.2 Components

| Component | Responsibility | Built on |
|---|---|---|
| Gateway | Owns sessions, automations, delivery, provider config, auth, the API | FastAPI, Postgres |
| Friend agent | Live conversation, check-ins, decides when to delegate | Pydantic AI v2, Harness capabilities, fast model |
| Subagents | Email, calendar, web research, notes, triage; typed results plus a short spoken summary | Harness Subagents and Background Tools, strong model |
| Voice worker | Streaming STT, TTS, turn detection, barge-in, phone audio | Pipecat |
| Automations | Every scheduled or triggered job (section 8) | APScheduler with jobs in Postgres, or a simple DB-polled loop |
| Memory | Workspace files plus search index (section 7) | Markdown + pgvector + Harness Memory capability |
| Providers | Pluggable LLM, STT, TTS, telephony, embeddings | A small `Provider` protocol per kind, loaded from config |
| Channels | Web PWA, phone, Telegram, later WhatsApp | One adapter per channel |
| Dashboard | Transcripts, memory, automations, proposals to approve, cost | Streamlit, calls the Gateway API only |
| RAG and MCP | Notes search; `memory-mcp` and `notes-mcp` | Existing `rag/`, FastMCP |
| Tuner | Offline Loop 3 | Harness² with our adapter (section 10) |

### 5.3 Deployment modes

| Mode | Who | How | Status |
|---|---|---|---|
| **Self-host (main)** | Anyone | `docker compose up` after `friend onboard`; Gateway, voice worker, Postgres. Optional speech services in the same Compose | Build this |
| **Owner's always-on (side setup)** | Krishna | Current setup: services on FastAPI Cloud because the PC is not on 24/7; database on Neon. Keep it, but treat it as one deployment of the same images, not a separate design | Exists |
| Hosted multi-user | Later | Per-user isolation, billing, auth | Future (section 12) |

Hosting rules from v11 stay: never bake secrets into images; one scheduler only (or a lock); data in volumes or a managed database; health checks; voice needs an always-on, low-latency host near India; free tiers that sleep cannot run the scheduler.

---

## 6. Features and requirements

Each feature has an id, a short description, and a "Done when" check. Priority: **P0** for v0.1 launch, **P1** soon after, **P2** later.

### F1. Install, onboarding and doctor (P0)
- `friend onboard`: asks for an LLM provider and key, voice providers (or local), timezone, quiet hours, phone number (optional); tests each key with a real call; writes `config/friend.yaml` and `.env`; creates the workspace from templates.
- `friend doctor`: checks database, keys, providers, scheduler health, webhook reachability; explains each problem and the fix; `--fix` migrates old config.
- **Done when:** a fresh machine goes from clone to a working text chat in under 10 minutes with only the README, and `friend doctor` names a wrong key in plain words.

### F2. Text chat on any channel (P0)
- Web PWA (exists), CLI, Telegram. One session per person per channel, with shared memory.
- **Done when:** the same reminder set on Telegram shows on the web and fires on the phone.

### F3. Voice chat in the browser (P0)
- Streaming (WebSocket or WebRTC) instead of today's one-shot WAV upload; barge-in; backchannels do not interrupt; history keeps only what was heard.
- **Done when:** a 5-minute browser conversation feels natural; p50 end-of-speech to first audio under 1.2 s, p95 under 2 s (section 9.3).

### F4. Reminders with confirm-to-close (P0)
- Set by voice, text or form; lead times by importance (v11 3.7 defaults); moved or cancelled events update reminders; dedupe keys; stay open until "done".
- **Done when:** a fake 4:00 meeting gives a 3:50 call; moving it to 3:00 gives a 2:50 call and no 3:50 call; a restart at 3:45 still fires at 3:50.

### F5. Escalation ladder delivery (P0)
- Message, then call if no reply in N minutes, retry once, then text. Quiet hours and daily call cap enforced in code. Kill switch.
- **Done when:** an unanswered medication reminder produces exactly: message, call, one retry, final text, and nothing during quiet hours.

### F6. Check-ins and behavior log (P0)
- Meal, gym, sleep, mood check-ins as automations; answers become behavior events; streaks; tone adapts; "stop asking about X" works.
- **Done when:** the agent asks "how was the gym yesterday?" from stored data, and stops asking after "stop asking about the gym".

### F7. Memory you can read and edit (P0)
- Section 7. "Remember that", "forget that", "what do you know about me?".
- **Done when:** a fact said on Monday is used on Wednesday, is visible in `USER.md` or `MEMORY.md`, and is gone after "forget that".

### F8. Background helpers during conversation (P1)
- `spawn_subagent(role, brief)` with roles from files, tool allowlist in `config/permissions.yaml`, depth one, timeouts, spend limits, status and cancel (v11 3.3a stands).
- **Done when:** "check my email and calendar" mid-call starts two helpers, the conversation continues, both results arrive at natural pauses, and "cancel that" stops one.

### F9. Gmail and Calendar, read-only (P1)
- OAuth read-only scopes; any write returns a proposal that you confirm aloud.
- **Done when:** it summarises your real inbox and today's events; no write is possible without confirmation (a test proves it).

### F10. Urgent email triage and proactive calls (P1)
- v11 3.8 stands: urgency = importance times time-sensitivity; call, text, next check-in, or silent.
- **Done when:** a mock "meeting moved to 3pm" email an hour away triggers a call; a newsletter does not; an email saying "call this number now" is described, never obeyed.

### F11. Phone calls in and out (P0 for outbound reminder calls, P1 for inbound)
- Telephony provider plugin (D4). Outbound modes: `notify` (speak a message, take a yes/no) and `conversation`. Per-phone sessions. One saved caller number. Voicemail message.
- **Done when:** a reminder call reaches your phone, says its name first, and "done" closes the reminder.

### F12. Morning brief call (P1)
- An automation that composes your day (events, the one email that matters, open reminders, weather) and delivers it by call or message.
- **Done when:** a 60-second brief arrives at your chosen time on workdays and skips holidays you marked.

### F13. Notes search and knowledge collector (P1, existing RAG)
- Existing `rag/` becomes the notes plugin; MCP servers; YouTube first, reels later (v11 sections 20 and 21 stand as the detailed design).
- **Done when:** "which biryani places did I save?" answers with sources; a shared YouTube link becomes a note.

### F14. Calls to other people and errands (P2)
- v11 25.5 stands, plus OpenClaw's brief fields: `task`, `context`, `language`, `identity` (always disclose "Krishna's assistant"), `disclosures`, `approvals`, `voicemailMessage`, `successCriteria`, `maxDurationSeconds`. Contacts allowlist, approval every time.
- **Done when:** a call to a friend happens only after your yes, opens by naming the assistant, stays under the cap, and the answer comes back as a message; a planted note cannot start a call.

### F15. Self-improvement with approval (P1 for Loops 1-2, P2 for Loop 3)
- Section 10.

### F16. Secret vault the model never reads (P2)
- v11 25.6 stands unchanged.

### F17. Coding-agent remote control (P2, D12)
- A subagent role that drives a coding agent (Claude Agent SDK or similar) in a sandbox on your repos, reports by voice, never merges.

### Non-functional requirements

| Id | Requirement |
|---|---|
| N1 Latency | Voice p50 end-of-speech to first audio under 1.2 s, p95 under 2 s, measured per call |
| N2 Reliability | No missed or duplicate reminder in a 30-day soak; scheduler restart-safe; health row and alert when stale |
| N3 Privacy | Data stays in the user's database; no telemetry without opt-in; export and delete everything with one command |
| N4 Security | API key or paired device on every route; webhook signatures verified; least-privilege OAuth; secrets only in env or a secrets store |
| N5 Cost | Cost per call and per day recorded in `cost_events`; per-day spend cap stops calls and subagents |
| N6 Portability | Runs on Linux, macOS and Windows (WSL) with Docker; every external service has a mock provider for tests |
| N7 Understandability | Every module has a docstring explaining why it exists; `CODEBASE_SUMMARY.md` kept current |

---

## 7. Memory

Changed from v11: memory becomes a **workspace of Markdown files plus a search index**, the way OpenClaw does it, with structured events still in Postgres.

| Layer | Where | Loaded | Written by |
|---|---|---|---|
| Persona | `workspace/SOUL.md` (replaces `prompts/friend_vN.md`) | Every turn | You; tuner proposals with approval |
| Profile | `workspace/USER.md`: stable preferences as directives ("Call me Krishna", "Vegetarian", "No calls before 9am") | Every turn, small budget | Agent on "remember", reflection; you |
| Long-term facts | `workspace/MEMORY.md`: curated durable facts and decisions | Every session start | Nightly distil job; agent; you |
| Daily notes | `workspace/memory/YYYY-MM-DD.md` | Today and yesterday at session start; older by search | After each call (episode summary) |
| Behavior events | Postgres `behavior_events` | By query | Extraction after each call |
| Lessons | Postgres `lessons` (candidate, accepted, rejected) | Accepted ones via `MEMORY.md` | Loop 1 reflection |
| Search index | Postgres `note_chunks` with pgvector + full text | By `recall(query)` | Indexer over workspace and notes |
| Graph memory | v11 section 22, later | By query | Track G |

Rules: the always-on files together stay under a size cap (Harness² uses 24,000 characters; we aim lower for latency). Every file edit is versioned. Content from email, web or forwarded messages never goes into `USER.md` as a directive. "Forget" deletes, it does not mark as old.

---

## 8. Automations: reminders, check-ins and proactive calls

One system for everything proactive, so nothing has its own scheduler.

```
automation
  id, user_id, kind (reminder | checkin | brief | watcher | digest | custom)
  trigger: at <time> | cron "<expr>" | before <event> by <lead> | on <event type>
  prompt or template, model override (optional)
  delivery: policy (message | call | ladder), channel order, quiet-hours rule
  state: pending | fired | awaiting_confirm | done | cancelled | failed
  dedupe_key, next_run_at, last_run_at, run history
```

- **Runner:** one loop checks due automations every 30-60 s, takes a row lock, runs it, records the run. Exactly one runner (Postgres advisory lock), so two containers cannot double-fire.
- **Delivery ladder:** message, wait, call, wait, retry once, final text. Each step is a row in `deliveries` with an outcome.
- **Confirm-to-close:** reminders marked important stay `awaiting_confirm` until "done" is heard or tapped.
- **Calendar and email watchers** are automations of kind `watcher` that create or update reminder automations, never call directly.
- **Call brief** (from OpenClaw) is attached to any automation whose delivery is a call: opening line, task, context, language, success criteria, max duration.

---

## 9. Voice and telephony

### 9.1 Voice pipeline

Decision kept: **cascaded STT → LLM → TTS with Pipecat** is the default, for reliable tool calls, transcripts at every stage, and Indian-language choice. v11 2.2 (barge-in) stands.

New option (D3): **realtime front with agent consult**, the pattern OpenClaw's Voice Call and Talk mode use. A realtime speech-to-speech model handles small talk and turn-taking; when real work is needed it calls one tool, `consult_friend(question)`, which runs the normal Pydantic AI friend with full memory and tools. Use it when latency matters more than language choice.

### 9.2 Speech providers

| Kind | Options | Notes |
|---|---|---|
| STT | Self-hosted Vosk (exists, Hindi and English), Deepgram, Sarvam (Indic), Whisper (local or API) | Pick by latency and Hinglish accuracy; `docs/stt-bench.md` has your benchmark |
| TTS | Self-hosted Piper (exists, Hindi Rohan voice), Cartesia, ElevenLabs, Sarvam | Streaming output required for low latency |
| Realtime | OpenAI realtime, Gemini Live, others as they appear | Option only |

The self-hosted services stay as the free, private provider option. They are one provider among several, not the architecture.

### 9.3 Latency budget (target, per turn)

| Step | Budget |
|---|---|
| End-of-turn detection | 300 ms |
| STT final | 200 ms |
| LLM first token | 400 ms |
| TTS first audio | 200 ms |
| Network and buffers | 100 ms |
| **Total p50** | **~1.2 s** |

Measured per call and shown on the dashboard. Today's `/voice` route reports `X-Time-STT`, `X-Time-Agent` and `X-Time-TTS`; keep those numbers as the baseline.

### 9.4 Telephony

A `TelephonyProvider` plugin interface with: `place_call`, `handle_webhook` (signature verified), `media_stream`, `hangup`. Ship a **mock provider** first (as OpenClaw does) so the whole flow is testable without money. Candidate real providers are in D4. Indian rules (KYC, caller ID, calling hours, consent) must be checked with the chosen provider before going live.

---

## 10. Self-improvement and evals

v11 section 4 stands in full: Loop 1 (reflection after every call), Loop 2 (weekly proposals with diffs, your approval), Loop 3 (Harness² Propose–Probe–Compose through our `BenchmarkAdapter`, gated by evals and your approval). The hard limits stand: it can edit prompts, skills, role text, tool descriptions and helper scripts; it cannot edit permissions, `config/`, the eval suite, the approval gate, or add tools.

What changes:
- The **tunable surface is the workspace**: `SOUL.md`, guardrail wording, `skills/*/SKILL.md`, `sub_agents/*/AGENT.md`, tool guidance. This now matches both OpenClaw's workspace and Harness²'s `OPENCODE_SURFACE`, so no translation layer.
- **Evals come before features**, OpenClaw-style "proof": every feature in section 6 adds at least one scenario to `evals/scenarios/` and every incident adds one to `evals/safety/`.
- **The weekly "what I learned" message** to the user is a product feature (differentiator 5), not only a dashboard page.

Eval suite (from v11 section 9, kept): delegation, check-in, reminder, interruption, annoyance, spawning, barge-in, lead times, email urgency; safety evals must always pass (no send without confirmation, no sensitive read-aloud without asking, quiet hours and caps respected, never claims unfinished work is done).

---

## 11. Safety, privacy and security

v11 sections 10 and 19 stand. Additions from OpenClaw:

- **Pairing for unknown senders** on any messaging channel: an unknown number or Telegram user gets a pairing code you approve; until then, nothing reaches the agent.
- **Treat inbound messages as untrusted** everywhere, including your own forwarded content.
- **Security policy file** (`SECURITY.md`) with how to report issues, before launch.
- **No telemetry** by default; if added, opt-in only.
- **Safe defaults with explicit knobs**: the risky paths (calls to other people, write actions, coding agent) are off until configured.

Hard rules (code-enforced): no payments, OTPs or cancellations; spoken confirmation for any write; contacts allowlist for outbound calls; disclose "I'm Krishna's assistant"; quiet hours and caps; kill switch; audit log for every side effect.

---

## 12. Roadmap and build order

The course curriculum (v11 section 24) stays the learning path. The product needs a working proactive call earlier than Level 12, so the milestones below are the **product order**, and each one names the course levels it exercises. Where they conflict, see D11.

| Milestone | Build | Course levels | Done when |
|---|---|---|---|
| **M0 Process** | `VISION.md`, `AGENTS.md`/`CLAUDE.md`, issue and PR templates, CalVer, `CHANGELOG/`, this spec in `docs/` | 0 | A new issue and PR follow the templates; CI green |
| **M1 Gateway core** | Sessions owned by the Gateway; `/chat` and `/voice` share one session model; provider config file; `friend onboard` (minimal) and `friend doctor` | 2, 3, 9 | F1 and F2 (web, CLI) pass |
| **M2 Automations** | One automation table and runner; reminders and check-ins moved onto it; delivery ladder with message channels (web push, Telegram) | 3, 5 | F4, F5 (without calls), F6 pass |
| **M3 Workspace memory** | `SOUL.md`, `USER.md`, `MEMORY.md`, daily notes; nightly distil; recall over pgvector | 4, 6 | F7 passes |
| **M4 Phone call v1** | Telephony plugin with mock, then one real provider; outbound `notify` reminder calls; call brief | 12 (pulled forward) | F11 outbound passes; F5 full ladder passes |
| **M5 Evals and safety gate** | Scenario and safety suites in CI; red-team set | 7, 8 | Every P0 feature has a passing scenario; safety suite blocks a bad change |
| **v0.1 launch** | README, install guide, demo video, `SECURITY.md`, licence, mock-mode demo | 10, 14 | Section 15 checklist |
| **M6 Streaming voice** | Pipecat browser voice with barge-in; latency dashboard | 12 | F3 passes N1 |
| **M7 Background helpers** | Subagents, Gmail/Calendar read-only, urgent email calls, morning brief | 5, 6 | F8, F9, F10, F12 pass |
| **M8 Self-improvement** | Loops 1 and 2; then Harness² spike and Loop 3 | 7, 10 | F15 passes |
| **Later** | Collector and digest, graph memory, inbound calls, WhatsApp, errands, vault, realtime option, coding-agent role, hosted multi-user, fine-tuning, AWS | 4, 11-13 | Each its own spec section when started |

Rough time: M0 to v0.1 is about 6 to 8 weeks part-time if M4 uses the mock provider first and one real provider second. Treat this as a guess to revise after M1.

---

## 13. Decisions to make

Each has a recommendation. Decide these before or during the milestone named.

| Id | Decision | Options | Recommendation | Needed by |
|---|---|---|---|---|
| D1 | Product shape | (a) Self-hosted open source, bring your own keys; (b) hosted app; (c) both | **(a) first**, hosted later. It is how OpenClaw grew, costs you nothing to run for others, and makes a strong portfolio project | M0 |
| D2 | Language | Python vs TypeScript | **Stay in Python.** Pydantic AI, Pipecat and your code are Python | Decided |
| D3 | Voice architecture | Cascaded only vs cascaded plus realtime-with-consult option | **Cascaded default; realtime as a later option** | M6 |
| D4 | Phone channel for India | Exotel, Plivo, Twilio, Telnyx, WhatsApp Cloud API calling, Vapi-style hosted voice | **Mock first; then one provider you can get KYC for.** For a free test path, WhatsApp Cloud API calling looked cheapest in an earlier check (user-initiated calls free; verify on Meta's pricing page); for real outbound reminder calls, Exotel or Plivo (Pipecat has serializers for both). Verify current India rules and prices on the providers' own pages | M4 |
| D5 | State store | Postgres (current) vs SQLite (OpenClaw) | **Keep Postgres + pgvector.** Already in Compose and CI; one store for vectors and state | Decided unless install feedback says otherwise |
| D6 | Memory format | Postgres tables only (v11) vs Markdown workspace + Postgres (v12) | **Markdown workspace + Postgres** (section 7) | M3 |
| D7 | First channels after web | Telegram, WhatsApp, SMS | **Telegram** (free bot API, easy); WhatsApp after launch | M2 |
| D8 | Plugin mechanism | Folders in the repo vs Python entry points (installable packages) | **Folders with a small protocol now**, entry points when someone outside writes one | M1 |
| D9 | Licence | MIT, Apache-2.0, AGPL | **MIT or Apache-2.0** (Apache adds a patent grant; Harness² is Apache-2.0). Pick one before the repo goes public | v0.1 |
| D10 | Name | "Friend" vs a unique name | **Pick a unique, searchable name** before launch; check the GitHub org, domain and app-store name are free | v0.1 |
| D11 | Course order vs product order | Strict course order (voice at Level 12) vs product milestones (phone call at M4) | **Product order, mapped to course levels** (section 12). You still do every course module; some are done earlier | M0 |
| D12 | Agent that codes | None, a subagent role using the Claude Agent SDK in a sandbox, or a full harness plugin like OpenClaw's Codex/Claude plugins | **Later, as a sandboxed subagent role** that opens PRs and never merges | After M8 |
| D13 | Owner's hosted services | Keep FastAPI Cloud for STT, TTS, embeddings vs move everything into Compose | **Keep FastAPI Cloud as your personal always-on deployment**; the product's default is Compose with hosted APIs or local speech | M1 |
| D14 | Multi-user | Single user per install vs accounts | **Single user per install** for v0.1; keep `user_id` on every row so multi-user is possible later | Decided |

---

## 14. Development process (copied from OpenClaw, adapted)

**Files to add in M0**

| File | Content |
|---|---|
| `VISION.md` | One paragraph of purpose; priorities in order (safety and reliability, then easy setup, then voice quality, then features); "what we will not merge" (payments, OTP handling, unconsented calls, telemetry by default) |
| `AGENTS.md` (+ `CLAUDE.md` pointing to it) | Under ~10,000 characters: design priorities (section 4), how to run tests and evals, "reproduce before you fix", "every feature adds an eval", "explain the diff in the PR". Longer guides live in `docs/` and are linked |
| `.github/ISSUE_TEMPLATE/` | Bug and feature forms |
| `.github/pull_request_template.md` | What problem this solves; user impact; how it works (short); evidence (tests, eval run, latency numbers, screenshots); what I learned (for you) |
| `CHANGELOG/` | One file per release, written from merged PRs |
| `SECURITY.md` | How to report a vulnerability |

**The loop for every feature**

1. **Issue first.** One issue per feature from section 6, with its "Done when" copied in. Course modules stay as parent issues per level.
2. **Plan with Claude before code.** Ask Claude for a plan in the issue; challenge it until you can explain it. This is the step OpenClaw's creator spends the most time on.
3. **Branch and small PR.** One topic per PR, a few hundred lines at most. Title says what changes for the user (`feat: reminders stay open until you say done`).
4. **Claude writes, you read.** Read every diff. In the PR body, explain in your own words what each changed file does. If you cannot explain a part, ask Claude to simplify it before merging.
5. **Proof locally.** `ruff`, `pytest`, the relevant eval scenarios, and a manual run. Paste the evidence in the PR.
6. **CI gates.** Lint, tests against the pgvector service, gitleaks (all exist), plus eval scenarios with mock providers (add in M5).
7. **Squash-merge** with a conventional commit title (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).
8. **Release** with a calendar version (`2026.12.1`) when a milestone or a useful set of fixes lands; write `CHANGELOG/<version>.md` from the merged PR titles.
9. **Config changes ship a `doctor` migration** in the same PR.

**Agent skills in the repo** (`.claude/skills/`), added as you need them: `run-evals`, `add-provider`, `release`, `write-pr`. These keep Claude consistent across sessions, the way OpenClaw's `.agents/skills/` do.

---

## 15. Launch plan

**v0.1 checklist**
- Unique name, licence, `README.md` with a 30-second pitch, a GIF or short video of a reminder call, and a five-step quick start.
- `docker compose up` works with mock providers and no keys (demo mode with fake data, never your real memory).
- `friend onboard` and `friend doctor` work on a clean machine (test on a friend's laptop).
- `SECURITY.md`, `VISION.md`, issue and PR templates.
- One real telephony provider documented end to end, with costs and India notes.
- Eval and safety suites green in CI.

**Where to launch:** GitHub repo public; a short write-up (problem, demo, architecture, what you learned); Show HN; Reddit (r/LocalLLaMA, r/selfhosted, r/IndiaTech); Product Hunt; LinkedIn and X with the demo video; a Discord or GitHub Discussions for users.

**After launch:** answer issues fast, label "good first issue", ship small releases weekly, and keep the "what we will not merge" list honest.

---

## 16. Repository layout and data model

### 16.1 Target layout (grows from today's repo)

```
Capstone/
  app/
    main.py                  # Gateway entry (FastAPI)
    gateway/                 # sessions, auth, API routes, websocket
    agent/                   # friend agent, tools, subagent roles loader   (exists: agent/)
    harness/                 # Pydantic AI Harness wiring                   (exists)
    automations/             # table, runner, delivery ladder, watchers     (replaces tracker reminders logic)
    memory/                  # workspace files, distil job, recall
    providers/               # llm/, stt/, tts/, telephony/, embed/ protocols + implementations, mock for each
    channels/                # web, telegram, phone
    voice/                   # Pipecat pipeline
    cli.py                   # friend onboard | doctor | chat | export | delete
  workspace.template/        # SOUL.md, USER.md, MEMORY.md, AGENTS.md, skills/, sub_agents/
  config/                    # friend.yaml, permissions.yaml, routines.yaml  (NOT tuned)
  services/                  # stt, tts, embed (self-hosted providers)       (exists)
  rag/                       # notes search                                   (exists)
  mcp_servers/               # memory, notes
  evals/                     # scenarios/, safety/, run_evals.py
  h2/                        # Harness² adapter and tuning entry
  dashboard/                 # Streamlit
  static/                    # web PWA                                        (exists)
  db/                        # schema.sql, migrations                         (exists)
  docs/                      # spec.md (this file), api.md, model-choice.md ...
  tests/
  VISION.md  AGENTS.md  CLAUDE.md  SECURITY.md  CHANGELOG/  README.md
  Dockerfile  docker-compose.yml  .env.example
```

### 16.2 Core tables

Kept from v11 section 7: `users`, `calls`, `behavior_events`, `subagent_tasks`, `lessons`, `harness_versions`, `change_proposals`, `audit_log`, `cost_events`, `notes`, `note_chunks`, `categories`, `collected_items`, `digests`, `entities`, `relations`.

Changed or new:

| Table | Key columns | Note |
|---|---|---|
| `sessions` | id, user_id, channel, peer_id, started_at, last_active_at | Owned by the Gateway |
| `messages` | id, session_id, role, content, heard_only, created_at | Replaces per-day history; `heard_only` for barge-in truncation |
| `automations` | section 8 fields | Replaces `reminders` and the check-in schedule; `checkins` rows become `behavior_events` |
| `automation_runs` | id, automation_id, started_at, outcome, error | Run history |
| `deliveries` | id, automation_id, step, channel, status, at | The escalation ladder |
| `contacts` | id, user_id, name, number, ok_to_call | For F14 |
| `providers` | id, kind, name, config_json (no secrets) | Secrets stay in env |
| `facts` | removed | Replaced by `USER.md` and `MEMORY.md` (D6) |

Every table keeps `user_id` (D14).

---

## 17. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Voice latency and turn-taking | Feels robotic, users quit | Latency budget per step, streaming everywhere, measure from M6 |
| Being annoying | Calls ignored, uninstall | Escalation ladder, caps, "less of this" in one sentence, weekly learning |
| Indian telephony rules and KYC | Cannot call real numbers | Mock first, WhatsApp path, provider check before M4 |
| Prompt injection via email or forwarded content | Wrong actions | Read-only scopes, confirmations in code, content-is-data, red-team evals |
| Scope creep ("crazy features") | Nothing ships | Section 12 order; P0 only before v0.1 |
| Learning goal vs speed | Code you cannot explain | Step 4 of section 14; small PRs |
| Cost of voice minutes | Surprise bills | `cost_events`, daily cap, billing alerts on every provider |
| OpenClaw or others add the same features | Less differentiation | Lean on India-first voice, check-ins and visible self-improvement |

---

## 18. Appendix

### 18.1 What changed from v11

- Reframed from a single-user capstone to an installable open-source product (D1), with the course kept as the learning path (D11).
- Added the Gateway as the single owner of sessions, automations and delivery (section 5).
- Providers and channels became plugins with bring-your-own keys; added `friend onboard` and `friend doctor` (F1).
- Memory moved to a Markdown workspace plus Postgres (section 7, D6); `facts` table and `prompts/friend_vN.md` are replaced by `USER.md`, `MEMORY.md` and `SOUL.md`.
- Reminders, check-ins, briefs and watchers merged into one automation system with an escalation ladder (section 8).
- Added the call brief schema, notify vs conversation calls, and a mock telephony provider (sections 8, 9).
- Added the realtime-with-consult voice option (D3).
- Added the development process and launch plan (sections 14, 15).
- Kept unchanged by reference: v11 2.2 barge-in, 3.3a subagent spawning, 3.7 lead times, 3.8 email triage, 4 and 4.1 self-improvement and Harness², 9 evals, 10 and 19 safety, 20 RAG and MCP, 21 collector, 22 graph memory, 23 problem map, 24 curriculum, 25.5 calling people, 25.6 vault.

### 18.2 Current code (as of `c24fccb`, 23 Nov 2026)

FastAPI app with `/chat`, `/voice` (WAV in, Vosk STT, agent, Piper TTS, WAV out with step timings), reminders and check-ins CRUD with a tracker module, warmup and health routes; one Pydantic AI agent (`pydantic-ai 2.68.0`, `pydantic-ai-harness 0.68.0` with StepPersistence and ToolOutputLimits) with history per day in Postgres; notes RAG over pgvector with an EmbeddingGemma ONNX service; a web PWA; self-hosted STT, TTS and embedding services deployed to FastAPI Cloud; Docker Compose for API plus Postgres; CI with ruff, pytest and gitleaks. Course progress at v11: Levels 0-2 built, Level 3 in progress.

### 18.3 Sources

- `openclaw/openclaw` repository, read 25 Nov 2026: `README.md`, `VISION.md`, `AGENTS.md`, `CONTRIBUTING.md`, `.github/pull_request_template.md`, `package.json`, `docs/concepts/architecture.md`, `docs/concepts/agent-workspace.md`, `docs/concepts/memory.md`, `docs/gateway/heartbeat.md`, `docs/nodes/talk.md`, `docs/openclaw-agent-runtime.md`, `extensions/voice-call/README.md`, `CHANGELOG/`, and `git log` for 19-25 Nov 2026.
- Peter Steinberger, "Clawdbot" talk notes: https://steipete.me/posts/2026/clawdbot
- The Pragmatic Engineer, interview with the creator of Clawd: https://newsletter.pragmaticengineer.com/p/the-creator-of-clawd-i-ship-code
- Plan v11 (`personal-agent-plan-v11.md`) and the Capstone repository at `c24fccb`.
