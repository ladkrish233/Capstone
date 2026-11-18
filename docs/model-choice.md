# Model choice (M1.10 to M1.12)

One row per job. Update it when you measure something. "TBD" means not decided yet.
Prices are per million tokens and were checked on 2026-11-10 on the vendor pricing page.

## How I choose

1. Does it do the job correctly on my own test cases? Accuracy comes first.
2. How much does it cost per run? (I log this in the `cost_events` table.)
3. How fast is it? Voice needs the first token in well under a second.
4. Does it support tools and structured output reliably?
5. Where does my data go? Real reminders and emails need a privacy check first.

## The table

| Job | Current choice | Evidence so far | Fallback | Decide later |
|---|---|---|---|---|
| Friend chat and tool use | `claude-haiku-5-5` through the Anthropic API | Input $0.10, output $0.50. "Plan my day" (2 model requests, 2 tool calls) used about 2,200 input and 170 output tokens, about $0.0003. Tools were picked correctly on my 10 test prompts. | `openrouter:deepseek/deepseek-chat` through `ModelFallback`, with a 20 second timeout | Re-check with data at Level 7 |
| Extraction (`parse_reminder`) | Anthropic Haiku model | Models can ignore prompt rules: one clamped a lead time of 300 to 240 and wrote `<UNKNOWN>` as a title. Code checks are needed on top of the prompt. | An OpenRouter model | Compare 3 models on my own cases at Level 7 |
| Planning and subagents | TBD | Not started | | Level 5 |
| Urgency scoring (email) | TBD | Not started. The prompted baseline is measured first (M13.1). | | Level 13 |
| Embeddings | TBD | Not started | | Compare two models at M4.3 |
| Speech to text (STT) | TBD. Candidates: Deepgram, faster-whisper (local) | Must be tested on Hinglish | | M12.6 |
| Text to speech (TTS) | TBD. Candidates: ElevenLabs, Cartesia, Piper (local), Paradee (local) | Paradee: about 8M parameters, one voice, about 25x faster than real time on one CPU thread, weights released. Not yet checked: licence, languages (Hinglish), and whether a version 1.2 exists. Judge all on latency, voice quality and Hinglish. | | M12.6 |

## Plan: models behind LiteLLM (M9.3, M11.7)

The chat and fallback models above are what runs today, with calls made straight to the Anthropic API and `ModelFallback` in the code. They are temporary. The plan is to put a LiteLLM gateway in front of every model. When that happens:

- The code asks for a role alias, such as `friend-chat` or `extraction`, not a vendor model. The alias-to-model mapping lives in the LiteLLM `config.yaml`, so changing a model is a config edit.
- Retries, timeouts and fallbacks move into the LiteLLM config (`num_retries`, `request_timeout`, `fallbacks`). The Pydantic AI `ModelFallback` in the code then becomes optional.
- Pydantic AI reaches LiteLLM through its OpenAI-compatible API: an `OpenAIChatModel` with an `OpenAIProvider` whose client points at the LiteLLM proxy `base_url`.
- Costs: LiteLLM can report spend itself. Decide then whether `cost_events` keeps its own price table or reads the cost from LiteLLM.

Until then, do not refactor. Record the role-to-model choice in the table above.

## Notes from testing

- Haiku 4.5 costs $1 input and $5 output. Haiku 5.5 costs one tenth of that ($0.10 and $0.50) for prompts up to 100,000 tokens. The cost function must use the price of the model that actually answered, which is why `run_cost` takes the model name.
- A cheaper model is not always worse. Measure accuracy before assuming it.
- A key must have credits on the account it belongs to. An OpenRouter key without credits returns a 402 error.

## Decision log

| Date | Decision | Reason |
|---|---|---|
| 2026-11-10 | Friend chat uses `claude-haiku-5-5` | Cheap, supports tools, passed my 10 tool prompts |
| 2026-11-10 | Fallback model through `ModelFallback` | The first model can fail or time out |
