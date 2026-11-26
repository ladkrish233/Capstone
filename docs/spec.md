# Rafi: product and build spec (v12.4)

Rafi is a voice-first personal friend and assistant that remembers you, checks in on you, calls you when something matters, and does background work while it keeps talking. Open source, self-hostable, bring your own model and voice keys.

This spec replaces the build plan `personal-agent-plan-v11.md`. It keeps every decision from v11 that still holds, reorganises the plan as a product spec, and adds what we learned from studying how OpenClaw is built and developed (section 2).

| | |
|---|---|
| Status | Draft for review, 25 Nov 2026. v12.1 added your decisions (Pydantic AI + Harness, FastAPI, React, local Postgres, Rafi the giraffe), free hosting and positioning. v12.2 added the capability map (5.5) and OpenClaw's community process (2.5). v12.3: full scope with Pipecat, Agent settings in the app (5.6), connectors and Twilio, planned around your exams (12.1). v12.4: built by mid-December, UI for configuration and chat only (12.1) |
| Owner | Krishna |
| Repo | `ladkrish233/Capstone` |
| Replaces | Plan v11 (kept as history; section numbers below are new) |
| How to use it | Section 12.1 is the plan around your exams. Section 5.5 says which framework feature does each job, and 5.6 how the app's settings reach the agent. Section 13 lists the decisions to make first. Every feature in section 6 has a "Done when" check |

---

## Contents

1. Summary
2. What we learned from OpenClaw (including how it reached people)
3. Product: who it is for, the landscape, and why it wins
4. Principles
5. Architecture (where it runs, free hosting, Pydantic AI and Harness map, Agent settings, Google's agent rules)
6. Features and requirements
7. Memory
8. Automations: reminders, check-ins and proactive calls
9. Voice and telephony
10. Self-improvement and evals
11. Safety, privacy and security
12. Roadmap: plan around your exams, then after launch
13. Decisions to make
14. Development process (copied from OpenClaw, adapted)
15. Launch plan and the Rafi landing page
16. Repository layout and data model
17. Risks
18. Appendix: what changed from v11, current code, sources

---

## 1. Summary

**What:** Rafi (the product, with a giraffe mascot named Rafi; see D10) is an AI friend plus personal assistant that you talk to by voice or text. It remembers your routines and preferences, checks in on meals, gym, sleep and mood, reminds you of what matters by actually calling you, hands slow work (email, calendar, web, notes) to background helpers while the conversation continues, and gets better from your feedback with your approval.

**For whom:** first for Krishna (daily use is the test), then for anyone who installs it on their own machine or server with their own API keys, the way people install OpenClaw. A hosted version is optional and later.

**Stack in one line (decided):** Python 3.13; built fully on **Pydantic AI v2 + Pydantic AI Harness** for every agent, tool, memory layer, subagent and guardrail; **Pipecat** voice pipeline with the Pydantic AI agent inside it (realtime as an option, D3); pgtask for durable reminders; **FastAPI** backend (the Gateway); a **React** web app for users and for the owner dashboard (replaces Streamlit and the current static PWA); **Postgres + pgvector running locally** (Neon is only the current development database); Docker Compose for a single-command install; Logfire (tracing); Harness² (offline tuning).

**Where it runs (decided):** first on Krishna's own computer; then a proper single Docker command anyone can run. Free always-on hosting for the parts that must never sleep is in section 5.4.

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
| Setup | One-line installer, `openclaw onboard` wizard (verifies model access, creates the workspace, installs the daemon), `openclaw doctor --fix` repairs and migrates old config | `rafi onboard` and `rafi doctor` (section 6, F1) |
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

OpenClaw can already place and receive phone calls (Voice Call plugin), run errands by phone with a brief, and run scheduled jobs. Several small apps also "call you with reminders". So "an AI that calls you" is not a moat by itself. Our edge has to come from sections 3.3 and 3.4.

### 2.5 How OpenClaw got to people (the community process to copy)

Read from the OpenClaw repo on 25 Nov 2026 (`README.md`, `CONTRIBUTING.md`, `.github/`).

| Area | What OpenClaw does | What Rafi does at launch | Later |
|---|---|---|---|
| Install | One-line installer for macOS, Linux and Windows that also installs the right Node; the installer opens the onboarding wizard by itself; `openclaw doctor --fix` repairs setups; ready deploy files (`docker-compose.yml`, `fly.toml`, `render.yaml`) | `git clone` + `docker compose up`; the React app opens a first-run setup page (keys, phone, quiet hours) and a Health page that checks each key (the "doctor") | `install.sh`, CLI `rafi onboard` and `rafi doctor`, deploy files for Oracle and Cloud Run |
| Where people ask | Blank issues are off. Issue forms for bugs, docs bugs and features; setup questions go to a community site and Discord, not to issues | Issue forms (bug, feature); blank issues off; questions go to GitHub Discussions | Discord when people ask for it |
| Bug reports | The form asks only for what was observed: summary, steps, expected vs actual, version, OS, install method, model, provider chain, logs, impact | Same fields, cut to: what happened, steps, expected, version, install method, model and phone provider, logs | |
| Contributions | `CONTRIBUTING.md` starts with a routing table: bugs and small fixes go straight to a PR; features start as an issue or a Discord chat; most features should be plugins; refactor-only PRs are refused; 20 open PRs per author at most | Short `CONTRIBUTING.md` with the same routing table and "explain your change in the PR" | Plugin guide once there is a plugin interface |
| Pull requests | PR template: problem, user impact, evidence, `Closes #issue`; `CODEOWNERS`, a labeler and auto-response workflows route and label work so nobody guesses who to tag | PR template (problem, user impact, evidence, what I learned); labels: `bug`, `feature`, `good first issue`, `voice`, `phone`, `india` | Labeler and auto-response bots |
| Releases | Calendar versions about three a week, changelog from merged PRs, Docker images, beta channel, update notice inside the app | First release `2026.11.30` with `CHANGELOG/2026.11.30.md` from the PR titles; Docker images built in CI | Weekly releases; update notice in the app |
| Docs | A `docs/` site kept current by a docs workflow, translations, a `GLOSSARY.md` | README quick start (five steps) + `docs/` pages: install, phone setup, providers, FAQ | Docs site, Hindi docs |
| Security | `SECURITY.md`, CodeQL, dependency audits, secret scanning, security review policy | `SECURITY.md`, gitleaks (exists), Dependabot | CodeQL |
| Brand and voice | A mascot (Clawd the lobster), playful words ("Welcome to the lobster tank!"), a public X account | Rafi the giraffe on the landing page and README, friendly tone | Stickers, a Rafi voice |

**The habit that matters most:** OpenClaw shipped something people could run very early (a one-hour WhatsApp relay), then grew by use, with issue first, one topic per PR and frequent small releases. Rafi's first release follows that: small, runnable, honest about what is missing.

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

### 3.4 The landscape and where Rafi fits (checked 25 Nov 2026)

There are many voice agents. They fall into six groups, and none of them combines what Rafi does.

| Group | Examples | Strong at | What they don't do (Rafi's opening) |
|---|---|---|---|
| Big-lab voice assistants | ChatGPT Voice and GPT-Live, Gemini Live, Alexa+, Siri, Grok voice | Best voice quality and knowledge; Gemini Live acts in Gmail, Docs and Sheets; Alexa+ is proactive around the home | You open the app first; they don't phone you about your day; memory is hidden; you can't self-host or choose providers; some agentic features are US and English only |
| Companion apps | Sesame (Maya and Miles), Pi, Replika, Kindroid | Warm, natural, emotional conversation | Talk only: no reminders, email, calendar or background tasks; Sesame sessions reportedly cut off near 30 minutes |
| Reminder-call apps | Gemma (Product Hunt, Feb 2026: calls you instead of notifying, syncs Google Calendar), Zangy, RemyVox | Prove the core insight: people ignore notifications but answer calls | Reminders only: no friend, memory, check-ins, background work, Indian languages or self-hosting |
| Voice-agent platforms for businesses | Vapi, Retell, Bland, Bolna, ElevenLabs agents, Hume EVI | Telephony and speech plumbing, priced per minute | Toolkits for companies to build call bots, not a personal assistant for one person |
| Open-source personal agents | OpenClaw (chat-first; voice-call plugin, cron automations, Markdown memory), Vellum's assistant (Mac; reaches out by text or Slack), Leon 2.0 (preview; proactive "pulse"), Jan, AnythingLLM, PyGPT | Private, self-hosted, extensible | Chat or desktop first; voice and phone are add-ons; none is built around check-ins and calling you in Indian languages |
| Indian AI apps | Indus by Sarvam (Feb 2026; type or speak in Indian languages; India-only beta) | Indian languages and voice | A chat app you open; launch coverage mentions no proactive calls, reminders or personal memory |

**The gap:** nobody combines (1) proactive phone calls with an escalation ladder, (2) a friend that remembers you and checks in, (3) real background work while the call continues, (4) Hindi, Hinglish and Indian phone channels, and (5) open source you run yourself with your own keys.

**Rafi's three strongest differentiators**

1. **It calls you, and it knows you.** Reminder-call apps prove calls beat notifications but stop at reminders. Rafi adds memory-driven check-ins, an escalation ladder (message, call, retry, text) and confirm-to-close.
2. **India-first and yours.** Hindi, Hinglish and Indian English, Indian phone and WhatsApp channels, open source on your own machine with your own keys, and cheap local speech (Vosk, Piper) or Indic providers (Sarvam). Big labs and OpenClaw are English-first and chat-first.
3. **Keeps talking while it works, and gets better where you can see it.** Background helpers run mid-call and report at natural pauses, and every week Rafi says what it learned and asks you to approve changes.

**Brand:** Rafi the giraffe. A giraffe's long neck sees what's coming, which is the product's promise (a proactive friend). Possible tagline: "Rafi sees what's coming."

**What would erase the edge:** a big lab shipping "it calls you" with memory in Indian languages, or OpenClaw making voice-first check-ins a default. Watch for both; the open-source, self-hosted and India-first parts are the hardest for them to copy.

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
   React app    Phone (provider     Telegram     CLI / TUI      React owner
   (voice+text)  webhook + media)   (later WA)   (rafi ...)     dashboard
        │              │               │             │               │
        └──────────────┴───────┬───────┴─────────────┴───────────────┘
                               ▼  HTTP + WebSocket API (typed, API key / paired device)
┌──────────────────────────────────────────────────────────────────────────┐
│ GATEWAY (FastAPI, one long-running process)                               │
│                                                                           │
│  Sessions ── one per channel+person; history in Postgres                  │
│  Rafi agent (Pydantic AI + Harness capabilities, fast model)              │
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
| Rafi agent | Live conversation, check-ins, decides when to delegate | Pydantic AI v2, Harness capabilities, fast model |
| Subagents | Email, calendar, web research, notes, triage; run one at a time, in parallel, or from a dynamic flow, each switchable in the app | Harness `SubAgents`, `BackgroundTools`, `DynamicWorkflow` via `RafiTeam` (5.6) |
| Voice worker | Talk in the browser and on the phone | Pipecat (STT, Rafi agent, TTS) with Twilio; optional realtime toggle (D3) |
| Automations | Every scheduled or triggered job (section 8) | pgtask (durable Postgres tasks) + Harness `PGTaskDurability` |
| Memory | Notebook files plus conversation recall (section 7) | Harness `Memory` (Postgres store), `StepPersistence`, `ConversationSearch`; pgvector notes search later |
| Providers | Pluggable LLM, STT, TTS, telephony, embeddings | A small `Provider` protocol per kind, loaded from config |
| Channels | React web app, phone, Telegram, later WhatsApp | One adapter per channel |
| Web app (React) | Two jobs only: **chat** (type, voice button, Call me button; reminders, approvals and helper progress inline) and **configuration** (Agent, Providers, Connectors, Phone, Persona and memory, Health). Installable as a PWA. A dashboard for transcripts and costs comes later | React + Vite + TypeScript, served by the Gateway, calls the Gateway API only |
| RAG and MCP | Notes search; `memory-mcp` and `notes-mcp` | Existing `rag/`, FastMCP |
| Tuner | Offline Loop 3 | Harness² with our adapter (section 10) |

### 5.3 Deployment modes

| Mode | Who | How | Status |
|---|---|---|---|
| **Your computer (stage 1)** | Krishna | Everything runs locally in Docker Compose, including Postgres with pgvector. Neon stays only until the local database is the default | Build this first |
| **Self-host for anyone (stage 2)** | Anyone | One command (`docker compose up`; the one-line installer comes later), then the first-run Setup page (D17); Gateway, voice worker, local Postgres, optional local speech services | v0.1 |
| **Always-on helper (side setup)** | Krishna | The PC is not on 24/7, so the parts that must never sleep (scheduler, phone webhooks) need a host; today STT, TTS and embeddings are on FastAPI Cloud and the database on Neon. Same images, not a separate design. Options in 5.4 | Exists, to be moved |
| Hosted multi-user | Later | Per-user isolation, billing, auth | Future (section 12) |

Hosting rules from v11 stay: never bake secrets into images; one scheduler only (or a lock); data in volumes or a managed database; health checks; voice needs an always-on, low-latency host near India; free tiers that sleep cannot run the scheduler.

### 5.4 Free hosting for the always-on parts

The PC is off at night, so anything that must never sleep needs a host: the scheduler and delivery ladder, phone webhooks, and the database they use. The voice worker is needed only during calls. Speech and embeddings can be hosted APIs or the self-hosted services. Free tiers change often; figures below are from the providers' docs or comparison pages read on 25 Nov 2026 (dates in the sources). Verify each on the provider's own page before signing up.

| Option | Free allowance | Sleeps? | Card needed | Fit for Rafi | Catch |
|---|---|---|---|---|---|
| **Your PC + Cloudflare Tunnel** | Free | Whenever the PC is off | No | Stage 1 development; phone webhooks reach your PC without opening ports | Not always-on |
| **Oracle Cloud Always Free (Arm VM)** | 2 OCPUs and 12 GB RAM (halved from 4 and 24 on 18 Aug 2026), 200 GB block storage, two small AMD VMs | No, but an instance idle for 7 days (under 20% CPU, network and memory) may be reclaimed | Yes, card and phone | Runs the same Docker Compose stack 24/7: Gateway, scheduler, local Postgres, even Vosk and Piper | It is a VM you look after (Docker on top); free compute only in your home region, so choose an Indian region at sign-up if offered; A1 capacity can be scarce |
| **Google Cloud Run** | 180,000 vCPU-seconds, 360,000 GiB-seconds and 2M requests a month | Scales to zero | Yes, billing account | The Gateway and webhooks, woken every minute by a scheduler ping; pair with Neon | Cold starts; long voice calls burn vCPU-seconds (180,000 s is 50 hours of one vCPU); a budget alert does not stop spending |
| Koyeb | One service, 0.1 vCPU and 512 MB; Postgres with 5 compute-hours | Scales to zero after 1 h idle | $29 card hold | Small API only | Frankfurt or Washington only (far from India); too small for speech |
| Render | 750 instance-hours, 512 MB | Sleeps after 15 min, about 1 min to wake | No | Landing page or demo | A sleeping scheduler misses the 3:50 call; free Postgres expires after 30 days |
| Hugging Face Spaces | CPU Basic used to be 2 vCPU and 16 GB | After 48 h idle | – | Not recommended | 2026 forum reports: Docker Spaces marked paid and new free accounts get no CPU Basic quota |
| Fly.io, Railway | Fly: $5 of usage a month with a card; Railway: $5 trial, then $1 a month | – | Fly yes | Not free enough for always-on | Fly bills the whole month once usage passes $5 |
| FastAPI Cloud (current) | Free terms not checked | – | – | Today's STT, TTS and embedding services | Verify its current free plan before relying on it |
| Neon (current database) | 100 compute-hours a month, 1 GB per project | Scales to zero after 5 min idle | No | Database for a Cloud Run setup | 1 GB; the end state is local Postgres |
| Cloudflare Pages, GitHub Pages | Free static hosting | No | No | The landing page (15.1) | Static only |

**Top three picks**

1. **Oracle Cloud Always Free Arm VM** for the always-on helper: the only free option big enough to run the whole Compose stack, including Postgres and local speech, around the clock. Keep a little steady load (the scheduler ticking every minute) and check the reclaim rule.
2. **Google Cloud Run + Neon** if you don't want to manage a VM: the Gateway scales to zero and a scheduler ping wakes it every minute; Neon holds the database. Use hosted STT and TTS, since local speech models don't suit scale-to-zero.
3. **Your PC + Cloudflare Tunnel** for everyday development, plus **Cloudflare Pages or GitHub Pages** for the Rafi landing page.

For users of the product the default is simpler: Rafi runs on their own computer with one command; the always-on helper is an optional add-on documented in the install guide.

### 5.5 Pydantic AI and Harness: what we use where

Checked against the installed versions (`pydantic-ai-slim` 2.68.0, `pydantic-ai-harness` 0.68.0) on 25 Nov 2026. The rule: **if the framework has it, we configure it instead of writing it.** "Toggle" means it appears as a switch in the React app's Agent settings (5.6). "v0.1" means it ships in the first public release (12.1).

| Rafi needs | Use | What it saves us from writing | When |
|---|---|---|---|
| **Agent settings from the UI** | Core `AgentSpec`: the whole agent (model, instructions, settings, capabilities) is one JSON document. `AgentSpec.model_json_schema_with_capabilities()` produces the JSON Schema for every capability, and `Agent.from_spec()` builds the agent from it (checked: Harness `Memory`, `BackgroundTools`, `SpendLimits`, `DetectLoops`, `Skills` and `ConversationSearch` all serialise) | A hand-built settings API and form for each capability | v0.1 |
| Remember the conversation across restarts | Harness `StepPersistence` with `PostgresStepStore` (already in the repo) | Our own sessions and history tables | v0.1 (exists) |
| "What did I tell you last week?" | Harness `ConversationSearch` (BM25 over the persisted steps) | A search over old chats | v0.1, toggle |
| Long chats and calls stay inside the model's context | Harness `SlidingWindowCompaction` or `SummarizingCompaction` | Trimming and summarising code | v0.1, toggle |
| Memory you can read and edit | Harness `Memory` with `PostgresMemoryStore`: a `MEMORY.md` notebook plus files, with `write`, `read`, `search` and `delete` memory tools; per-user namespace; safe concurrent writes | Our own memory files, loader and tools (section 7) | v0.1, toggle |
| Rafi's personality | `SOUL.md` as agent instructions (editable in the app); Harness `SystemReminders` re-states key rules during long calls | Prompt-assembly code | v0.1 |
| Behaviours without code | Harness `Skills`: `SKILL.md` files loaded only when needed; users add their own | Hard-coded flows | v0.1, toggle |
| Keeps talking while it works | Harness `BackgroundTools`: tools marked `background` run while the conversation continues | Task juggling (v11 3.3a) | v0.1, toggle |
| **Subagents** | Harness `SubAgents`: one `delegate_task` tool over named helpers (email, research, calendar), each with its own model; an optional model menu lets Rafi pick a fast or strong model per task | Delegation code | v0.1, toggle per helper |
| **Parallel agents** | Harness `SubAgents` run in the background (with `BackgroundTools`), so several helpers work at the same time while Rafi talks | Fan-out code | v0.1, toggle |
| **Dynamic flows** | Harness `DynamicWorkflow`: Rafi writes a short Python script that calls helpers as functions (fan-out, chaining, voting, retries) and runs it in the Monty sandbox (`pydantic-ai-harness[dynamic-workflow]`) | A workflow engine | v0.1, toggle (off by default) |
| Answer questions from the web | Harness `KeenableSearch` (no key) or core `WebSearch` and `WebFetch` | Search tool code | v0.1, toggle |
| Tool calls that don't break | Harness `RepairToolArguments` (installed), `ToolOutputLimits` (exists), `DetectLoops` | Retry and clean-up code | v0.1 (always on) |
| Users bring their own keys, so cost must be capped | Harness `SpendLimits` (daily budget) and core `UsageLimits` per run | Cost tracking | v0.1, setting |
| One provider is down | Core `ModelFallback` | Failover code | v0.1, setting |
| **Models from the user's own provider** | Pydantic AI providers (OpenAI, Anthropic, Google, Groq, Mistral, OpenRouter, Ollama and others) picked by `provider:model` string; key entered once in the app | Provider clients | v0.1 |
| **Connectors** | Harness `GitHub`, `GoogleWorkspace` (Gmail, Calendar, Drive through Google's hosted MCP servers), `Slack`, `Notion`, `Linear` integrations, plus core MCP support so a user can add any MCP server by URL | API clients for each app | v0.1: GitHub, Google Workspace, any MCP URL; others later |
| Ask before acting for you | Core deferred tools with approval and `RequestInput` (approval cards in the app); Harness `ApprovalReviewer` clears low-risk calls | An approvals system | v0.1 (needed once connectors can act) |
| Safety when email and web text flow in | Harness `ToolGuardrail`, `InputGuardrail`, `PromptInjectionDefender`, `ArtifactScanning` (checks memory and skill files) | Filters | v0.1 with connectors |
| Reminders, check-ins and the escalation ladder that survive crashes | **pgtask** (Postgres task queue: `run_at`, durable `sleep_until`, `wait_for_signal`, idempotency keys, cancel, retries) with Harness `PGTaskDurability` | The scheduler, locks, retries and de-duplication in section 8 | v0.1 |
| Chat UI in React | Core `VercelAIAdapter`: one FastAPI endpoint streaming to the Vercel AI SDK's `useChat` hook; `agent.to_web()` as a stopgap chat page while the app is built | Streaming protocol code | v0.1 |
| Voice in the browser and on the phone | **Pipecat** pipeline (STT, Rafi agent, TTS) with Twilio over WebSocket; the Pydantic AI agent is the "LLM" stage (5.6). Optional toggle: core realtime (`agent.realtime(model).session()`) on Gemini Live or OpenAI Realtime for lowest latency | A voice stack | v0.1 (Pipecat); realtime toggle if time allows |
| Tests of behaviour | `pydantic-evals` (installed) in CI; Harness `TrajectoryJudge` and `ToolCallJudge` later | An eval runner | v0.1 |
| Tracing and cost view | Logfire instrumentation (exists) | Logging code | v0.1 (exists) |
| Notes search without LangChain | Core embeddings + pgvector | Keeps D16 | After launch |
| Self-improvement | Logfire `ManagedPrompt`, judges; `CapabilityCreation` only in a sandbox | Prompt versioning | After launch |
| Errands in a browser; coding agent | Harness `Playwright` or `BrowserUse`; `Coder` in `DockerSandbox` | Automation and coding harness | Later |

**Checked and not used, and why:** cloud sandboxes (Daytona, E2B, Modal, Boxd, BoxLite, Smol, Sprites, OpenSandbox, Render, Bubblewrap, SSH) because Monty covers dynamic flows; other durability engines (Temporal, DBOS, Prefect, AWS Lambda, Azure, Absurd) because pgtask uses our Postgres; work-tool MCP connectors (PostHog, Pylon, Ordinal, Grain, Day AI, StackOne) because they are not personal; Exa and You.com (paid search, Keenable first); `CodeMode`, `Planning`, `Advisor`, `AskUser` (`RequestInput` covers questions); developer tools (`PydanticAIDocs`, `RepoContext`, `SmartSearch`, `Macroscope`, `WarnOnCacheBusts`) which help Claude while you code, not Rafi itself; the experimental ACP adapter.

### 5.6 Agent settings: how a switch in the app reaches the agent

```
React Agent settings page                    FastAPI Gateway                         Runtime
  form generated from the JSON Schema  --->  GET /api/agent/schema  (AgentSpec schema with capabilities)
  switches, model pickers, budgets     --->  PUT /api/agent/spec    (validate, save new version in Postgres)
                                             build_agent(spec)  -->  Agent.from_spec(spec,
                                                                       custom_capability_types=HARNESS_CAPS,
                                                                       toolsets=connectors_from_db())
                                                                     used by chat, phone (Pipecat) and pgtask workers
```

- **One settings document per user**, stored as versioned JSON (`agent_specs` table), so a bad change can be rolled back in one click. The next run picks it up; no restart.
- **The UI has two jobs: configuration and chat** (your call, 25 Nov). Chat offers typing, a voice button and a Call me button; everything else is a Settings tab (Agent, Providers, Connectors, Phone, Persona and memory, Health).
- **The form is generated**, not hand-built: the React page renders the JSON Schema (for example with `react-jsonschema-form`), with a curated top section (on/off switches for Memory, Subagents, Parallel, Dynamic flows, Web search, Background work, Budget) and an "Advanced" section that shows every capability's own parameters. A new Harness capability appears in the app by adding it to `HARNESS_CAPS`.
- **Subagents, parallel agents and dynamic flows:** `SubAgents` takes live `Agent` objects, so it does not serialise directly. We add one small custom capability, `RafiTeam`, whose spec lists helpers by name, model, instructions and connectors, plus two flags (`parallel`, `dynamic_flows`). At build time it creates the helper agents and returns `SubAgents` (and `BackgroundTools`, `DynamicWorkflow` when switched on). This is the main piece of custom code in the agent layer.
- **Providers and keys:** a Providers page per kind (LLM, STT, TTS, phone, embeddings). Keys are stored encrypted in Postgres (or read from `.env`), never shown again after saving, and each has a **Test** button. Model fields are `provider:model` strings validated by Pydantic AI.
- **Connectors page:** GitHub (token), Google Workspace (Google sign-in), any MCP server URL. Each connector becomes a toolset passed into `from_spec`, and can be given to the main agent or to specific helpers. Actions that change things (send mail, create an issue) need approval by default.
- **Twilio:** account SID, auth token and number on the Providers page; the app shows the webhook URL to paste into Twilio (local installs use Cloudflare Tunnel). The Pipecat phone pipeline uses the same `build_agent(spec)`, so settings apply to calls too. A **Test call** button rings your number.
- **Speed:** the voice agent streams its reply into TTS sentence by sentence; a fast model is the default for voice and a strong model for helpers (set per helper in settings); slow tools run in the background; latency per stage is shown on the Health page (target in 9.3).

### 5.7 Google Workspace: Google's rules for AI agents (from 1 Feb 2027)

Google Cloud emailed you about this on 24 Nov 2026, and the same rules are on Google's developer site and in its new Workspace AI Tools Addendum (both read 26 Nov 2026). They apply to Rafi's Google Workspace connector.

| What changes | When | What it means for Rafi |
|---|---|---|
| AI agents must reach Workspace data through Google's MCP servers, not by calling the Gmail, Drive or Calendar REST APIs directly. An agent that calls REST directly is held to Standard tier quotas | Enforced 1 Feb 2027 | Already the plan: Harness `GoogleWorkspace` talks to Google's hosted MCP servers (`gmailmcp`, `calendarmcp`, `drivemcp` at `.googleapis.com/mcp/v1`; checked in `pydantic-ai-harness` 0.68.0). No direct REST calls to Workspace anywhere in Rafi, including the urgent-email check (F10) and the morning brief (F12). F9 uses `read_only=True` |
| The OAuth client must have "Use this client for an AI-powered agent" ticked in Google Auth Platform, and the Gmail, Calendar and Drive MCP services must be enabled in the Cloud project | Now | Part of the 25-26 Nov prep and of the install docs. Each user makes their own Cloud project and OAuth client (Google's "Personal mode" setup does it in one go). Rafi runs its own Google sign-in and passes the token to `GoogleWorkspace(auth=...)`, since Google doesn't support automatic OAuth client registration |
| Two usage tiers. Standard: free, no billing account, 5,000 requests a day per project per product on the MCP servers, plus per-minute limits. Scaled: billed from the first MCP request for Gmail, Calendar and Drive | Tiers live 24 Nov 2026; billing from 1 Apr 2027 | One person's use should fit in Standard. Keep polling light (no minute-by-minute inbox checks) and show Google request counts on the Health page |
| Workspace AI Tools Addendum: use Workspace data only for active tasks the user asked for; keep "Google Technical Information" (Google names vector embeddings, memory indexes, user profiles and findings) no longer than 30 days; keep nothing after the user disconnects or revokes access; no model training, fine-tuning or building eval datasets with it; no scraping beyond what a task needs | 1 Feb 2027 | Tag every memory entry, daily-note line and `note_chunks` row that came from Gmail, Drive or Calendar with its source; delete it after 30 days, and at once when the user disconnects Google. Don't index the inbox or Drive ahead of time; fetch on demand. Keep Workspace content out of self-improvement data and evals (section 10). D20 |

**Not confirmed:**
- Whether a summary or fact Rafi writes from an email counts as Google Technical Information (30-day limit) or as user data (governed by Google's Workspace user data policy, with no fixed period). The Addendum names embeddings and memory indexes but doesn't define user data, so the 30-day rule above is the safe reading.
- Whether the rules cover a personal, self-hosted install. Google lists no exemption, and the Addendum applies to whoever uses or authorizes an agent, so plan as if they do.
- Whether a background check that involves no model (for example, counting unread mail) counts as agent access. Route it through MCP anyway.

---

## 6. Features and requirements

Each feature has an id, a short description, and a "Done when" check. Priority: **P0** for v0.1 launch, **P1** soon after, **P2** later.

### F1. Install, onboarding and doctor (P0)
- `rafi onboard`: asks for an LLM provider and key, voice providers (or local), timezone, quiet hours, phone number (optional); tests each key with a real call; writes `config/rafi.yaml` and `.env`; creates the workspace from templates.
- `rafi doctor`: checks database, keys, providers, scheduler health, webhook reachability; explains each problem and the fix; `--fix` migrates old config.
- **Done when:** a fresh machine goes from clone to a working text chat in under 10 minutes with only the README, and `rafi doctor` names a wrong key in plain words.

### F2. Text chat on any channel (P0)
- React web app (replaces today's static PWA), CLI, Telegram. One session per person per channel, with shared memory.
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

**v0.1:** the table above is the target. In v0.1 it is three framework pieces: `SOUL.md` as instructions, Harness `Memory` (a `MEMORY.md` notebook plus files, stored in Postgres, editable in the React app) and `ConversationSearch` over past conversations. Daily notes, the nightly distil job, behaviour events and lessons come after launch.

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

**v0.1 implementation:** the automation table above is the target model; in v0.1 each reminder is one durable **pgtask** workflow, so the runner, locks, retries and de-duplication come from pgtask, and a crash never repeats a finished step. A sketch (names illustrative; check pgtask's docs for how a signal timeout is reported):

```python
@tasks.task("reminder")
async def reminder(task: Task, r: dict) -> dict:
    await task.sleep_until("due", datetime.fromisoformat(r["at"]))
    for i, step in enumerate(["notify", "call", "call", "sms"]):
        await task.step(f"{step}-{i}", lambda: deliver(step, r))      # app push, Twilio call or SMS
        if step == "sms":
            break
        if await done_within(task, f"wait-{i}", minutes=5 if i == 0 else 10):
            return {"closed_by": step}                               # "done" button, keypress 1 or the agent's mark_done tool
    return {"closed_by": None}
```

The reminder's pgtask id is stored with the reminder, so "cancel" and "done" are `cancel()` and `emit_signal(..., "done", ...)` calls. Recurring check-ins enqueue their next run when they finish, with an idempotency key per date.

---

## 9. Voice and telephony

### 9.1 Voice pipeline

**Decided (your message of 25 Nov): Pipecat** is the voice pipeline for v0.1, in the browser and on the phone: STT, then the Rafi agent (built from the same settings as chat, 5.6), then TTS, with Pipecat's Twilio transport, turn detection and interruptions (v11 2.2 barge-in stands). Rafi's reply streams into TTS sentence by sentence, and slow tools run in the background, so the voice keeps moving.

**Optional toggle:** Pydantic AI realtime (`agent.realtime(model).session()`) runs the same agent on Gemini Live or OpenAI Realtime for the lowest latency, at the cost of fewer provider choices. Pydantic AI's own comparison page says its realtime support has no built-in phone layer and no cascaded pipeline, which is why Pipecat stays the main path.

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

## 12. Roadmap: plan around your exams, then after launch

### 12.1 Plan around your exams (build 4-14 Dec 2026)

**Timeline:** prep on 25-26 Nov; **no coding during exams, 27 Nov to 3 Dec** (assumed end date; move every date below if it differs); build from 4 to 14 Dec so it is **built by mid-December**; **soft launch Tue 15 Dec**; big launch (Show HN, Product Hunt, Reddit) on **Mon 4 Jan 2027** after fixes over the holidays (D18).

**Scope:** Pipecat voice in the browser and on the phone; every Pydantic AI and Harness capability that fits, switchable in settings (5.5, 5.6); your own providers and keys; connectors (GitHub, Google Workspace, any MCP server); Twilio so calling works. **The UI has two jobs only: configuration and chat.** The chat screen has three ways to talk: type, a voice button (talk in the browser) and a **Call me** button (Rafi phones you). Real phone calls also come from reminders and check-ins. Reminders, approvals and helper progress show inside the chat, not on pages of their own.

**Honest view:** 11 build days is tight for this scope. Four parts are real work: the Pipecat phone pipeline with Twilio, Google sign-in for Google Workspace, the generated settings form, and the `RafiTeam` capability. If a phase slips, drop in this order: the realtime voice toggle, Slack and Notion connectors, incoming calls, dynamic flows (keep subagents and parallel). The launch keeps its date; what slipped goes in the next release.

| Dates | Phase | Build | Done when |
|---|---|---|---|
| **Wed 25 - Thu 26 Nov** | Prep (no heavy coding) | Decisions D9 and D18. Process files (2.5): `VISION.md`, `AGENTS.md` + `CLAUDE.md`, `CONTRIBUTING.md`, issue forms, PR template, `SECURITY.md`, labels. One issue per row below. Accounts and keys: one LLM key (Twilio is upgraded later, before 8 Dec, see D4), a Google Cloud OAuth client for Workspace ("Use this client for an AI-powered agent" ticked, Gmail, Calendar and Drive MCP services enabled; 5.7), Cloudflare Tunnel | Issues exist |
| **27 Nov - 3 Dec** | Exams | Nothing | |
| **Fri 4 - Sat 5 Dec** | Brain from settings | `agent_specs` table; `build_agent(spec)` with `Agent.from_spec`; `RafiTeam` (subagents, parallel, dynamic flows); persistence, memory, search, compaction, skills, budget, fallback; providers with user keys; pgtask worker and the reminder ladder on a mock phone; evals in CI | Changing the spec turns subagents on and off without a restart; a reminder survives a worker crash; evals green |
| **Sun 6 - Mon 7 Dec** | React app (config + chat) | **Chat:** text with streaming (`useChat` + `VercelAIAdapter`), tool calls, helper progress, reminders and approval cards inline; voice button; Call me button. **Settings:** Agent (generated form, curated switches, version history), Providers with Test buttons, Connectors, Phone (Twilio keys, webhook URL, Test call), Persona and memory (`SOUL.md`, `MEMORY.md`), Health; first-run setup | A fresh install is set up and chatting from the browser alone; a switch in settings changes the next answer |
| **Tue 8 - Thu 10 Dec** | Voice and phone | Pipecat pipeline with the Rafi agent as the LLM stage, streaming sentence by sentence; browser voice; Twilio outbound calls (Call me, the reminder ladder with "say done or press 1"), incoming calls, SMS fallback; STT and TTS choice (Deepgram, Sarvam, Cartesia, ElevenLabs, local Vosk and Piper); latency per stage on Health. Stretch: realtime toggle | Call me rings your phone and you talk to Rafi; a real reminder call closes on "done"; p50 turn latency measured |
| **Fri 11 - Sat 12 Dec** | Connectors | GitHub; Google Workspace (Gmail, Calendar, Drive) with Google sign-in; any MCP server by URL; per-helper connector access; approvals for actions; guardrails on incoming email and web text; morning brief and urgent-email call as skills | "What's on my calendar tomorrow?" works by voice; an email draft needs your approval |
| **Sun 13 - Mon 14 Dec** | Ship | Demo mode (mock phone, fake data); one command (`docker compose up`); README, docs pages, landing page on Cloudflare Pages, demo video, licence, release `2026.12.15` with changelog; test on a friend's laptop | A friend installs from the README alone and gets a call from Rafi |
| **Tue 15 Dec** | Soft launch | Repo public; posts on LinkedIn and X; early users in GitHub Discussions | |
| **16 Dec - 3 Jan** | Fix | Weekly releases from early users' issues; anything cut from the build goes here | |
| **Mon 4 Jan 2027** | Big launch | Show HN, Product Hunt, r/selfhosted, r/LocalLLaMA, r/IndiaTech | |

**After launch:** Indian phone provider (Exotel or Plivo after KYC), WhatsApp and Telegram, Slack and Notion if not shipped, notes search without LangChain, self-improvement loops, calls to other people, vault, coding agent, CLI `onboard`/`doctor` and `install.sh`, multi-user, a separate dashboard for transcripts and costs.

### 12.2 After launch (the milestone order)

The course curriculum (v11 section 24) stays the learning path. The product needs a working proactive call earlier than Level 12, so the milestones below are the **product order**, and each one names the course levels it exercises. Where they conflict, see D11.

| Milestone | Build | Course levels | Done when |
|---|---|---|---|
| **M0 Process** | `VISION.md`, `AGENTS.md`/`CLAUDE.md`, issue and PR templates, CalVer, `CHANGELOG/`, this spec in `docs/` | 0 | A new issue and PR follow the templates; CI green |
| **M1 Gateway core** | Sessions owned by the Gateway; `/chat` and `/voice` share one session model; provider config file; `rafi onboard` (minimal) and `rafi doctor`; React app shell (chat and reminders) replaces `static/`; local Postgres is the default | 2, 3, 9 | F1 and F2 (web, CLI) pass |
| **M2 Automations** | One automation table and runner; reminders and check-ins moved onto it; delivery ladder with message channels (web push, Telegram) | 3, 5 | F4, F5 (without calls), F6 pass |
| **M3 Workspace memory** | `SOUL.md`, `USER.md`, `MEMORY.md`, daily notes; nightly distil; recall over pgvector | 4, 6 | F7 passes |
| **M4 Phone call v1** | Telephony plugin with mock, then one real provider; outbound `notify` reminder calls; call brief | 12 (pulled forward) | F11 outbound passes; F5 full ladder passes |
| **M5 Evals and safety gate** | Scenario and safety suites in CI; red-team set | 7, 8 | Every P0 feature has a passing scenario; safety suite blocks a bad change |
| **v0.1 launch** | README, install guide, demo video, `SECURITY.md`, licence, mock-mode demo, Rafi landing page (15.1) | 10, 14 | Section 15 checklist |
| **M6 Streaming voice** | Pipecat browser voice with barge-in; latency dashboard | 12 | F3 passes N1 |
| **M7 Background helpers** | Subagents, Gmail/Calendar read-only, urgent email calls, morning brief | 5, 6 | F8, F9, F10, F12 pass |
| **M8 Self-improvement** | Loops 1 and 2 with proposals approved in the React dashboard; then Harness² spike and Loop 3 | 7, 10 | F15 passes |
| **Later** | Collector and digest, graph memory, inbound calls, WhatsApp, errands, vault, realtime option, coding-agent role, hosted multi-user, fine-tuning, AWS | 4, 11-13 | Each its own spec section when started |

These milestones now describe the order **after** the 15 Dec release; the plan in 12.1 covers the build up to it. Treat the order as a guess to revise after launch.

---

## 13. Decisions to make

Each has a recommendation. Decide these before or during the milestone named.

| Id | Decision | Options | Recommendation | Needed by |
|---|---|---|---|---|
| D1 | Product shape | (a) Self-hosted open source, bring your own keys; (b) hosted app; (c) both | **(a) first**, hosted later. It is how OpenClaw grew, costs you nothing to run for others, and makes a strong portfolio project | M0 |
| D2 | Language | Python vs TypeScript | **Stay in Python.** Pydantic AI, Pipecat and your code are Python | Decided |
| D3 | Voice architecture | Pipecat cascaded (STT, LLM, TTS) vs Pydantic AI realtime speech-to-speech | **Decided: Pipecat** with the Pydantic AI agent as its LLM stage; realtime as an optional toggle | Decided (25 Nov) |
| D4 | Phone channel for India | Exotel, Plivo, Twilio, Telnyx, WhatsApp Cloud API calling, Vapi-style hosted voice | **Decided: Twilio first, on an upgraded (paid) account** (checked 26 Nov on Twilio's pages: a trial blocks `<Stream>`, which Pipecat needs, and calls only within your own country; upgraded, a US number (from $1.15/month) calls Indian mobiles at $0.0496/min and Twilio keeps that caller ID, since calls to India must come from a non-Indian number; each user brings their own account). Exotel ruled out for v0.1 (26 Nov): KYC needs business documents, voice streaming is a separate offering outside its plans (from Rs 9,999), trial is 7 days. After launch: one Indian provider you can get KYC for. For a free test path, WhatsApp Cloud API calling looked cheapest in an earlier check (user-initiated calls free; verify on Meta's pricing page); for real outbound reminder calls, Exotel or Plivo (Pipecat has serializers for both). Verify current India rules and prices on the providers' own pages | Decided (25 Nov) |
| D5 | State store | Neon (current) vs local Postgres vs SQLite (OpenClaw) | **Decided: local Postgres + pgvector** in Docker Compose. Neon only while developing (and optionally for a Cloud Run always-on helper) | Decided |
| D6 | Memory format | Postgres tables only (v11) vs Markdown workspace + Postgres (v12) | **Markdown workspace + Postgres** (section 7) | M3 |
| D7 | First channels after web | Telegram, WhatsApp, SMS | **Telegram** (free bot API, easy); WhatsApp after launch | M2 |
| D8 | Plugin mechanism | Folders in the repo vs Python entry points (installable packages) | **Folders with a small protocol now**, entry points when someone outside writes one | M1 |
| D9 | Licence | MIT, Apache-2.0, AGPL | **MIT or Apache-2.0** (Apache adds a patent grant; Harness² is Apache-2.0). Pick one before the repo goes public | Before 15 Dec |
| D10 | Name and mascot | "Friend" vs a unique name | **Decided: mascot Rafi the giraffe; product name Rafi** unless the name check fails. Before launch check the GitHub org, a domain, app-store names and existing trademarks for "Rafi" | Name check by v0.1 |
| D11 | Course order vs product order | Strict course order (voice at Level 12) vs product milestones (phone call at M4) | **Product order, mapped to course levels** (section 12). You still do every course module; some are done earlier | M0 |
| D12 | Agent that codes | None, a subagent role using the Claude Agent SDK in a sandbox, or a full harness plugin like OpenClaw's Codex/Claude plugins | **Later, as a sandboxed subagent role** that opens PRs and never merges | After M8 |
| D13 | Always-on hosting for your own use | FastAPI Cloud + Neon (current), Oracle Always Free VM, Cloud Run + Neon (5.4) | **Oracle Always Free VM running the same Compose stack**; Cloud Run + Neon if you'd rather not manage a VM. The product default stays on the user's own computer | M2 (when the scheduler must never sleep) |
| D15 | Frontend | Streamlit dashboard + static PWA vs React | **Decided: React** (Vite + TypeScript) for both the user app and the owner dashboard, installable as a PWA; Streamlit is dropped | Decided |
| D16 | Agent framework | Pydantic AI + Harness vs mixing in LangChain or LangGraph | **Decided: build fully on Pydantic AI + Pydantic AI Harness.** Consequence: v11's LangChain and LangGraph RAG plan becomes Pydantic AI tools plus plain Python (loaders, chunking, pgvector queries); remove LangChain from the runtime dependencies over time | Decided |
| D17 | Onboarding for v0.1 | CLI wizard (`rafi onboard`, `rafi doctor`) vs a first-run Setup page and Health page in the React app | **Setup and Health pages in the app** for v0.1 (less code, nothing to install); CLI later | Recommended |
| D18 | Launch dates | Nov 30 is off because of exams (27 Nov - 3 Dec); you want it built by mid-December | **Soft launch Tue 15 Dec** (built by mid-December, your call on 25 Nov); **recommended big launch Mon 4 Jan 2027** after fixes over the holidays | Big launch date: before 15 Dec |
| D19 | Agent settings storage | Settings in `.env` and code vs one versioned `AgentSpec` JSON per user, edited in the app | **One versioned `AgentSpec`** (5.6), so every capability is a switch and changes can be rolled back | Recommended |
| D20 | Gmail, Drive and Calendar content in memory | Keep facts from them until "forget" vs keep them at most 30 days vs never store them (fetch each time) | **At most 30 days, deleted at once when Google is disconnected** (5.7). Keeping them until "forget" may break Google's terms from 1 Feb 2027 | Before 11 Dec (connectors) |
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

## 15. Launch plan and the Rafi landing page

**v0.1 checklist**
- Name check for Rafi (D10), licence, the landing page (15.1), `README.md` with a 30-second pitch, a GIF or short video of a reminder call, and a five-step quick start.
- `docker compose up` works with mock providers and no keys (demo mode with fake data, never your real memory).
- The Setup and Health pages work on a clean machine (test on a friend's laptop); CLI `rafi onboard` and `rafi doctor` come after launch (D17).
- `SECURITY.md`, `VISION.md`, issue and PR templates.
- One real telephony provider documented end to end, with costs and India notes.
- Eval and safety suites green in CI.

**Where to launch:** GitHub repo public; a short write-up (problem, demo, architecture, what you learned); Show HN; Reddit (r/LocalLLaMA, r/selfhosted, r/IndiaTech); Product Hunt; LinkedIn and X with the demo video; a Discord or GitHub Discussions for users.

**After launch:** answer issues fast, label "good first issue", ship small releases weekly, and keep the "what we will not merge" list honest.

### 15.1 The Rafi landing page

**Goal:** in 10 seconds a visitor understands "a friend who calls before you forget", hears a real call, and can copy one install command.

| Section | Content |
|---|---|
| Hero | Rafi the giraffe on a phone call; headline such as "Rafi sees what's coming"; one line: "An open-source voice friend that remembers you, checks in, and calls when it matters"; buttons: **Hear Rafi call** (audio demo) and **Run it in one command** (copyable command); GitHub star count |
| How it works | Three steps with Rafi illustrations: you tell Rafi (voice or text), Rafi remembers, Rafi calls at the right time and keeps calling until it's done |
| Demo | A 30-60 s recording of a real reminder call in Hinglish, with captions; a short video of "check my email" mid-call |
| Features | Calls with an escalation ladder; daily check-ins; keeps talking while it works; memory you can read; learns with your approval; bring your own models and keys; Hindi and Hinglish |
| Privacy | Runs on your computer, your data stays there, no telemetry by default |
| Honest comparison | A small table against reminder-call apps, big-lab assistants and chat-first agents (from 3.4), without naming claims you can't back |
| Install | The one command, system needs (Docker), and a link to the guide |
| FAQ | What it costs to run, which phone providers work in India, which languages, which models, is it safe |
| Footer | GitHub, docs, Discord or Discussions, licence, `SECURITY.md` |

**Mascot guidelines:** one consistent flat style in SVG that works on light and dark backgrounds; a small set of poses tied to product states: calling (phone), thinking (background work), sleeping (quiet hours), notebook (learning), waving (onboarding). Reuse the same poses in the React app's empty states and in the README.

**Build:** a static site (Astro, or Vite + React to share components with the app) in `site/`, deployed to Cloudflare Pages or GitHub Pages; Open Graph image with Rafi; no tracking scripts.

**Done when:** it loads in under a second on a mid-range phone, scores 90+ on Lighthouse, the demo plays, the install command copies, and it reads well in dark mode.

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
    cli.py                   # rafi onboard | doctor | chat | export | delete
  workspace.template/        # SOUL.md, USER.md, MEMORY.md, AGENTS.md, skills/, sub_agents/
  config/                    # rafi.yaml, permissions.yaml, routines.yaml  (NOT tuned)
  services/                  # stt, tts, embed (self-hosted providers)       (exists)
  rag/                       # notes search                                   (exists)
  mcp_servers/               # memory, notes
  evals/                     # scenarios/, safety/, run_evals.py
  h2/                        # Harness² adapter and tuning entry
  web/                       # React app (Vite + TS): user app + owner dashboard; replaces static/
  site/                      # Rafi landing page (static)
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
- Providers and channels became plugins with bring-your-own keys; added `rafi onboard` and `rafi doctor` (F1).
- Memory moved to a Markdown workspace plus Postgres (section 7, D6); `facts` table and `prompts/friend_vN.md` are replaced by `USER.md`, `MEMORY.md` and `SOUL.md`.
- Reminders, check-ins, briefs and watchers merged into one automation system with an escalation ladder (section 8).
- Added the call brief schema, notify vs conversation calls, and a mock telephony provider (sections 8, 9).
- Added the realtime-with-consult voice option (D3).
- Added the development process and launch plan (sections 14, 15).
- Kept unchanged by reference: v11 2.2 barge-in, 3.3a subagent spawning, 3.7 lead times, 3.8 email triage, 4 and 4.1 self-improvement and Harness², 9 evals, 10 and 19 safety, 20 RAG and MCP, 21 collector, 22 graph memory, 23 problem map, 24 curriculum, 25.5 calling people, 25.6 vault.

### 18.1b What changed in v12.1

- Decided: Pydantic AI + Harness for everything (D16), FastAPI backend, React frontend instead of Streamlit (D15), local Postgres instead of Neon (D5), run on your own computer first then one Docker command (5.3).
- Mascot and name: Rafi the giraffe (D10); CLI commands renamed `rafi onboard` and `rafi doctor`.
- Added the landscape and positioning (3.4), free hosting comparison (5.4) and the landing page (15.1).

### 18.1c What changed in v12.2

- Added 5.5: every Pydantic AI and Harness capability checked against the installed versions, with what Rafi uses, where, and what it saves us from writing.
- Added 2.5: how OpenClaw reached people (installer, onboarding, issue forms, routing, releases, docs, brand) and what Rafi copies by 30 Nov.
- Added 12.1: six-day plan to a soft launch on 30 Nov, with a clear cut list; the old milestones became the after-launch order.
- Scheduler changed to pgtask with `PGTaskDurability`; v0.1 voice proposed as Pydantic AI realtime (D3); Twilio proposed for v0.1 phone calls (D4); added D17 (onboarding in the app) and D18 (launch meaning).

### 18.1d What changed in v12.3

- Your exams (27 Nov - 3 Dec) moved the plan: build 4-20 Dec, soft launch 21 Dec, big launch 4 Jan 2027 (12.1). The six-day plan was removed.
- Full scope back in v0.1: Pipecat voice (D3 decided), Twilio first (D4 decided), connectors (GitHub, Google Workspace, any MCP server), approvals and guardrails.
- Added 5.6: Agent settings in the React app generated from `AgentSpec`'s JSON Schema; one agent with subagents, parallel agents and dynamic flows as switches through a small `RafiTeam` capability; providers, connectors and Twilio set up in the app.

### 18.1e What changed in v12.4

- Built by mid-December: build 4-14 Dec, soft launch Tue 15 Dec, big launch Mon 4 Jan 2027 recommended (12.1).
- The UI is only configuration and chat: chat has text, a voice button and a Call me button; reminders, approvals and helper progress show inside the chat; the rest are Settings tabs (5.6).

### 18.2 Current code (as of `c24fccb`, 23 Nov 2026)

FastAPI app with `/chat`, `/voice` (WAV in, Vosk STT, agent, Piper TTS, WAV out with step timings), reminders and check-ins CRUD with a tracker module, warmup and health routes; one Pydantic AI agent (`pydantic-ai 2.68.0`, `pydantic-ai-harness 0.68.0` with StepPersistence and ToolOutputLimits) with history per day in Postgres; notes RAG over pgvector with an EmbeddingGemma ONNX service; a web PWA; self-hosted STT, TTS and embedding services deployed to FastAPI Cloud; Docker Compose for API plus Postgres; CI with ruff, pytest and gitleaks. Course progress at v11: Levels 0-2 built, Level 3 in progress.

### 18.3 Sources

- `openclaw/openclaw` repository, read 25 Nov 2026: `README.md`, `VISION.md`, `AGENTS.md`, `CONTRIBUTING.md`, `.github/pull_request_template.md`, `package.json`, `docs/concepts/architecture.md`, `docs/concepts/agent-workspace.md`, `docs/concepts/memory.md`, `docs/gateway/heartbeat.md`, `docs/nodes/talk.md`, `docs/openclaw-agent-runtime.md`, `extensions/voice-call/README.md`, `CHANGELOG/`, and `git log` for 19-25 Nov 2026.
- Peter Steinberger, "Clawdbot" talk notes: https://steipete.me/posts/2026/clawdbot
- The Pragmatic Engineer, interview with the creator of Clawd: https://newsletter.pragmaticengineer.com/p/the-creator-of-clawd-i-ship-code
- Plan v11 (`personal-agent-plan-v11.md`) and the Capstone repository at `c24fccb`.
- Hosting: Oracle Always Free resources doc (https://docs.oracle.com/en-us/iaas/Content/FreeTier/resourceref.htm); SnapDeploy, "State of Free Hosting 2026" (a competitor's page; figures dated Sep 2026) (https://snapdeploy.dev/state-of-free-hosting); Flavio Copes, free tiers checked Sep 2026 (https://flaviocopes.com/hosting-free-tiers/); agentdeals.dev free FastAPI stack (Neon and Supabase limits) (https://agentdeals.dev/free-fastapi-stack); Hugging Face forum reports on CPU Basic quota (https://discuss.huggingface.co/t/free-cpu-basic-quota-is-0-on-new-account/180764); Oracle A1 cut coverage (https://labmemo.com/?p=55273).
- Frameworks: installed `pydantic-ai-slim` 2.68.0 and `pydantic-ai-harness` 0.68.0 (module docs and READMEs, read 25 Nov 2026); pgtask 0.4.0 on PyPI (https://pypi.org/project/pgtask/); Pydantic AI vs Pipecat (https://pydantic.dev/docs/ai/comparisons/vs-pipecat/); Harness docs (https://pydantic.dev/docs/ai/harness/).
- OpenClaw community process: `README.md`, `CONTRIBUTING.md`, `.github/ISSUE_TEMPLATE/` and `.github/workflows/` in the OpenClaw repo at commit `fca45c26a` (25 Nov 2026).
- Google's rules for agents (read 26 Nov 2026): Google Cloud's email of 24 Nov 2026; https://developers.google.com/workspace/tools-safety; https://developers.google.com/workspace/guides/configure-mcp-servers; https://workspace.google.com/terms/ai-tools; `pydantic_ai_harness/google_workspace` in 0.68.0.
- Landscape: PyAI, Sesame alternatives, Nov 2026 (https://pyai.com/blog/sesame-ai-alternatives); eesel, GPT-Live alternatives, Jul 2026 (https://www.eesel.ai/blog/gpt-live-alternatives); Vellum, open-source personal AI assistants, Sep 2026 (https://vellum.ai/blog/best-open-source-personal-ai-assistants); Gemma on Product Hunt (https://www.producthunt.com/products/gemma/launches/gemma-4); TechCrunch on Indus by Sarvam, Feb 2026 (https://techcrunch.com/2026/02/20/indias-sarvam-launches-indus-ai-chat-app-as-competition-heats-up/).
