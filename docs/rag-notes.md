# Level 4: RAG notes (M4.1 to M4.5)

Status: ingestion, chunking, embeddings and pgvector storage work. The agent tools (M4.6) are next.

## Pipeline

```
sources            load + clean            chunk              embed              store            search
-------            ------------            -----              -----              -----            ------
data/notes/*.md -> load_markdown()  \
data/pdfs/*.pdf -> load_pdfs()       > list[Doc] -> chunk_docs() -> embed_chunks() -> PGVectorStore -> search(query, k)
YouTube link    -> load_youtube_url()/   (rag/ingest.py)  (rag/chunk.py)  (rag/embed.py)    (rag/store.py)
```

| File | Functions | Input | Output |
|---|---|---|---|
| `rag/ingest.py` | `load_markdown`, `load_pdfs`, `load_youtube_url`, `clean`, `video_id`, `expand_playlist` | files, links | `list[Doc]` |
| `rag/chunk.py` | `to_document`, `chunk_docs` | `list[Doc]` | `list[Document]` with metadata |
| `rag/embed.py` | `embed_chunks`, `embed_query` | chunks, a question | vectors |
| `rag/store.py` | `add_chunks`, `search` | chunks, a question | `(Document, distance)` |

Metadata on every chunk: `doc_id`, `source`, `kind`, `title`, `chunk_index`.

## Decisions

| Topic | Decision | Why |
|---|---|---|
| Loaders | Plain Python, not LangChain loaders | Few lines each, full control over cleaning and errors |
| Chunking | LangChain `RecursiveCharacterTextSplitter`, size 800, overlap 100 | Good default; short notes stay as one chunk |
| Embeddings | `nvidia/nemotron-3-embed-1b:free` through OpenRouter, via LangChain `OpenAIEmbeddings` | Free, no local RAM, handled Hinglish in the test |
| Vector size | 2048 (fixed by the provider; `dimensions` other than 2048 returns a 400 error) | |
| Vector store | pgvector in the existing Postgres, `PGVectorStore` (not the deprecated `PGVector`) | One database for everything |
| Index | None for now (exact search) | pgvector indexes `vector` only up to 2,000 dims; our data is small. Later: `halfvec` expression index (limit 4,000) or switch to a 1,024-dim model such as `baai/bge-m3` |
| Docker image | `pgvector/pgvector:pg18` | Plain `postgres` has no pgvector |

## Ingest results

- Markdown: 55 documents (56 files; the empty note is skipped), 0 dirty documents (no front matter or HTML comments left).
- YouTube: 2 single videos and a playlist of 7 loaded in testing; transcripts need captions.
- PDFs: still to add (3 to 5 text PDFs in `data/pdfs`).
- Chunking: all 55 notes are under 500 characters, so each is one chunk at sizes 500, 800 and 1200. The size comparison only means something once PDFs and transcripts are loaded.

## Search quality test (55 synthetic notes)

Six fair questions plus one with no answer. Result: **6 of 6 correct at rank 1**, including both Hinglish questions.

| Question | Right note first | Similarity | Distance (pgvector) |
|---|---|---|---|
| How long does the City Palace visit take? | Udaipur | 0.315 | 0.685 |
| How do I make good tea? | Perfect chai | 0.365 | 0.635 |
| Chai kaise banate hain? (Hinglish) | Perfect chai | 0.311 | 0.689 |
| Which ice cream flavours are best? | Natural ice cream | 0.437 | 0.563 |
| Kitna protein khana chahiye? (Hinglish) | Diet notes | 0.308 | 0.692 |
| How do I use virtual environments? | Python tips | 0.374 | 0.626 |
| Who won the cricket world cup? (no answer) | none | 0.116 | 0.884 |

- `distance = 1 - similarity`. pgvector returns the distance (lower is closer).
- Every right answer has distance 0.69 or less; the best wrong match is 0.80 or more.
- **"Not found" threshold (starting value): best distance above 0.75 means Friend says it could not find that in the notes.** Adjust with real data.
- Limits of this test: short, easy, synthetic notes, one chunk each, only 2 Hinglish questions. Results show relative quality, not real-world accuracy.
- An earlier test used questions about iron, but no note covers iron. That test was unfair and its results are ignored. Always check that the answer exists in the data before writing a test question.

## How to run

```
docker compose up -d db                  # Docker Desktop must be running
python -m rag.ingest                     # load and count documents
python -m rag.chunk                      # chunk and compare sizes
python -m rag.store add                  # embed and store the chunks (run ONCE)
python -m rag.store                      # search the 7 test questions
```

To start the store over: `docker compose exec -T db psql -U postgres -d friend -c "TRUNCATE chunks;"`.

`.env` needs `OPENROUTER_API_KEY` and `VECTOR_DB_URL=postgresql+psycopg://postgres:<password>@localhost:5433/friend`. Never paste these in chat or commit `.env`.

## Gotchas hit along the way

- **Windows event loop.** psycopg async cannot use `ProactorEventLoop`. Set `asyncio.WindowsSelectorEventLoopPolicy()` at the top of `store.py` when `sys.platform == "win32"`.
- **Port.** The compose file maps the database to host port **5433**. Connecting on 5432 reached a different Postgres on the PC (no pgvector): "extension vector is not available".
- **Factory method.** Use `PGVectorStore.create_sync(engine=..., table_name=..., embedding_service=...)`, not `PGVectorStore(...)`.
- **Hidden errors.** A `try/except` around table creation hid the real error; print the exception while debugging. Table creation only needs to run in the `add` step.
- **Postgres 18 volume path.** Mount the volume at `/var/lib/postgresql`, not `/var/lib/postgresql/data`.
- **`numpy`** is needed by LangChain's in-memory store (`uv add numpy`).
- **`OpenAIEmbeddings`** needs `check_embedding_ctx_length=False` for non-OpenAI models.
- **YouTube IP block.** Many runs in a row triggered `IpBlocked`. Cache each transcript on disk (`data/cache/yt_<id>.txt`) and download it only once. Run on your own PC, not a cloud server.
- **Cache files.** Delete `data/cache/*` and truncate the table whenever the embedding model, chunk size or documents change. Never mix vectors from two models in one table.
- **Free models get retired.** Another free embedding model on OpenRouter was announced as going away on 16 November 2026. Keep `baai/bge-m3` ($0.01 per million tokens, 1,024 dims) as the fallback, and record the model name and dimension with the vectors. Re-embedding is cheap at this data size.
- **Privacy.** Do not embed real personal data (meals, mood, health) with a free endpoint until its data-retention policy is confirmed.
- **Git.** The repo lives in OneDrive on this PC; a corrupted `refs/remotes/origin/master` file was fixed by deleting it and running `git fetch`. Prefer a folder outside OneDrive.

## Next steps

1. Add 3 to 5 text PDFs to `data/pdfs`; add the YouTube transcript cache; rerun chunking and compare chunk sizes 500, 800, 1200.
2. Build an eval set of 15 to 20 questions written in your own words (English, Hinglish, a few unanswerable), measure hit@1 and hit@3, and re-run it whenever the model, chunk size or prompt changes.
3. M4.6: tools for the agent: `search_knowledge(query)` (apply the 0.75 distance cut-off, return chunks with sources, mark the text as outside data) and `save_video(url)` (only `youtube.com` and `youtu.be` links, small playlist limit).
4. Add a hostile-chunk case (an injected instruction inside a note or transcript) to the injection tests, and run it per model.

## Voice side notes (STT decision)

- Chosen STT: Vosk small Hindi (`vosk-model-small-hi-0.22`), its own app, WebSocket streaming later. Fallback: collabora tiny-hindi, then Groq whisper-large-v3-turbo.
- Benchmark (skeleton WER and CER): collabora 12.5% and 4.1%, Vosk 13.2% and 6.2%, whisper-tiny-hinglish 42.0% and 15.8% (rejected).
- Vosk on FastAPI Cloud Nano (0.1 vCPU, 500 MB): about 305 MB peak, a 10 s clip took about 2.3 s over 27 runs. Streaming should make it feel faster.
- Full details are in `stt-bench/README.md`.
