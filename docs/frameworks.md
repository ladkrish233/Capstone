# Orchestration frameworks for Voice Friend (M2.11)

Written 2026-11-10. These libraries change quickly, so re-check the docs before relying on a detail.

## What I compared

- **Pydantic AI**: the agent library the friend uses today.
- **LangChain**: an agent framework with a large set of model and tool integrations. Its agents are built on LangGraph.
- **LangGraph**: a low-level runtime for long-running, stateful workflows, written as a graph of nodes and edges.
- **OpenAI Agents SDK**: a lightweight agent framework with handoffs, guardrails, sessions and tracing.

## Comparison

| Question | Pydantic AI | LangChain | LangGraph | OpenAI Agents SDK |
|---|---|---|---|---|
| What is it for? | A typed agent loop: model, tools, structured output | Building agents with `create_agent` (model, tools, prompt, middleware) | Explicit control of state and flow for long-running agents | Lightweight agents that delegate, validate and trace |
| How do you define a tool? | A plain function. Its schema comes from the signature and docstring (`@agent.tool_plain`) | A type-hinted function with a docstring, passed in the `tools` list | Tools are called from nodes you write | Any Python function, with automatic schema and Pydantic validation |
| Structured output | Built in. A Pydantic model validates the result and retries on failure | Not checked in the docs I read | Up to the nodes you write | Not checked in the docs I read |
| Multi-step flows and state | One agent loop; Pydantic Graph is available for typed control flow | Built on LangGraph | The core feature: shared state, nodes, edges, checkpoints, human-in-the-loop | Handoffs between agents, sessions for memory |
| Model choice | Many providers; a model is a string; `ModelFallback` for failover | Many providers through one model interface | Usually uses LangChain's model integrations | OpenAI first; others through adapters such as LiteLLM |
| Tracing | OpenTelemetry-native; Logfire is the suggested backend | LangSmith | LangSmith | Built-in tracing, aimed at OpenAI's tools |
| Durable runs (survive restarts) | Supported through several engines (Temporal, DBOS, Prefect) | Through LangGraph | Built in (persistence) | Not checked |

## Verdict: why the friend uses Pydantic AI

1. **Typed output.** `parse_reminder` returns a validated `Reminder`. Bad values fail loudly instead of reaching the database.
2. **Simple tools.** `add_reminder`, `list_reminders`, `list_checkins` and `get_time` are ordinary async functions with a docstring. No extra classes are needed.
3. **Failover in one line.** `ModelFallback` switched to a second model when the first failed or timed out, and changing a model is a string edit.
4. **Tracing and cost.** Logfire works with two calls, and `usage` gives token counts that feed the `cost_events` table.
5. **Room to grow.** The same library supports MCP (Level 5), evals (Level 7), durable execution and a realtime voice interface (Level 12), so the friend does not need to change frameworks later.

## When I would switch or add another

- **LangGraph** for the email-triage workflow (fetch, classify, score, notify) if it needs checkpoints and a pause for human approval. This is planned for M5.7.
- **LangChain** for its ready-made document loaders and integrations when rebuilding the RAG pipeline (plan M4.15).
- **OpenAI Agents SDK** if the project moved fully to OpenAI models and wanted its built-in handoffs and tracing. The friend uses several providers, so this is unlikely.

## Pydantic AI vs LangChain, tested (M2.3)

I built the same small chat in both: one tool (`get_time`), the same Haiku model, and a loop that keeps the history.

| Question | Pydantic AI | LangChain |
|---|---|---|
| Lines to set up the agent | Similar | Similar |
| How a tool is defined | A decorator on the agent (`@agent.tool_plain`) | `@tool` on a standalone function, then passed in `tools=[...]` |
| How history is kept | Pass `message_history=...`, then add `result.new_messages()` | Send the whole list in, then replace my list with `result["messages"]` |
| How I ask the model | `agent.run_sync("text")` | `invoke({"messages": [{"role": "user", "content": "text"}]})`, a bit more to write |
| What I read for the reply | `result.output`, clean text | `result["messages"][-1].content`, which can be a list of blocks (a thinking block plus a text block), so the text has to be pulled out |
| Tracing | `logfire.configure()` and `logfire.instrument_pydantic_ai()` | LangSmith (set `LANGSMITH_TRACING=true` and a LangSmith API key). Not tried yet. |

What surprised me: the same chat needed almost the same code in both, but the LangChain reply came back as raw content blocks when the model used thinking, and I had to unpack it.

Verdict: both are similar for tools and history. I stay with Pydantic AI for the friend because its replies are clean to read, tracing is two lines with Logfire, and fallback is built in. LangChain stays on the list for its loaders and integrations when I rebuild the RAG pipeline.

## Sources

- Pydantic AI overview: https://pydantic.dev/docs/ai/overview/
- LangChain overview: https://docs.langchain.com/oss/python/langchain/overview
- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
- OpenAI Agents SDK: https://openai.github.io/openai-agents-python/
