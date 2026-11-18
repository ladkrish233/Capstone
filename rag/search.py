from pathlib import Path

from langchain_core.vectorstores import InMemoryVectorStore

from rag.chunk import chunk_docs
from rag.embed import embedder
from rag.ingest import (
    load_markdown,
)

STORE_FILE = Path("data/cache/store.json")
_store = None


def get_store() -> InMemoryVectorStore:
    global _store
    if _store is not None:
        return _store
    if STORE_FILE.exists():
        _store = InMemoryVectorStore.load(str(STORE_FILE), embedder)
    else:
        docs = load_markdown("data/notes")
        chunks = chunk_docs(docs)
        _store = InMemoryVectorStore.from_documents(chunks, embedder)
        STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _store.dump(str(STORE_FILE))
    return _store


def search(query: str, k: int = 3):
    return get_store().similarity_search_with_score(query, k=k)


QUESTIONS = [
    "how long does the City Palace visit take?",  # expect: Udaipur
    "how do I make good tea?",  # expect: Perfect chai
    "chai kaise banate hain?",  # expect: Perfect chai (Hinglish)
    "which ice cream flavours are best?",  # expect: Natural ice cream
    "kitna protein khana chahiye?",  # expect: Diet notes (Hinglish)
    "how do I use virtual environments?",  # expect: python-tips
    "who won the cricket world cup?",  # expect: nothing (low scores)
]


def main():
    for q in QUESTIONS:
        print(f"\nQ: {q}")
        for doc, score in search(q):
            m = doc.metadata
            print(
                f"  {score:.3f}  {m['title']} (chunk {m['chunk_index']})  {doc.page_content[:80]!r}"
            )


if __name__ == "__main__":
    main()
