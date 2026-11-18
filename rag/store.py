import asyncio
import os
import sys

from dotenv import load_dotenv
from langchain_postgres import PGEngine, PGVectorStore

from rag.chunk import chunk_docs
from rag.ingest import (
    load_csv,
    load_docx,
    load_html,
    load_markdown,
    load_pdfs,
    load_text,
)
from rag.remote_embed import RemoteEmbeddings

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()

TABLE = "chunks"
VECTOR_SIZE = 768

_engine = None
_store = None
URL = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+psycopg://", 1)


def get_engine():
    global _engine
    if _engine is None:
        _engine = PGEngine.from_connection_string(url=URL)
    return _engine


def get_store():
    global _store
    if _store is None:
        _store = PGVectorStore.create_sync(
            engine=get_engine(),
            table_name=TABLE,
            embedding_service=RemoteEmbeddings(),
        )
    return _store


def init_table():
    try:
        get_engine().init_vectorstore_table(table_name=TABLE, vector_size=VECTOR_SIZE)
    except Exception as e:  # fails if the table already exists
        if "already exist" in str(e):
            print("table already exists,skippings")
        else:
            raise


def add_chunks(chunks):
    get_store().add_documents(chunks)


def search(query: str, k: int = 3):
    return get_store().similarity_search_with_score(query, k=k)


QUESTIONS = [
    "how long does the City Palace visit take?",
    "how do I make good tea?",
    "chai kaise banate hain?",
    "which ice cream flavours are best?",
    "kitna protein khana chahiye?",
    "how do I use virtual environments?",
    "who won the cricket world cup?",
]


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "add":
        init_table()
        docs = (
            load_markdown("data/notes")
            + load_pdfs("data/pdfs")
            + load_csv("data/csv")
            + load_docx("data/docx")
            + load_html("data/html")
            + load_text("data/text")
        )
        chunks = chunk_docs(docs)
        add_chunks(chunks)
        print(f"added {len(chunks)} chunks from {len(docs)} documents")
        return

    for q in QUESTIONS:
        print(f"\nQ: {q}")
        for doc, score in search(q):
            m = doc.metadata
            print(
                f"  {score:.3f}  {m.get('title')} (chunk {m.get('chunk_index')})  {doc.page_content[:80]!r}"
            )


if __name__ == "__main__":
    main()
