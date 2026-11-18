from collections import Counter

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.ingest import Doc, load_markdown, load_pdfs


def to_document(d: Doc) -> Document:
    return Document(
        page_content=d.text,
        metadata={"doc_id": d.id, "source": d.source, "kind": d.kind, "title": d.title},
    )


def chunk_docs(docs: list[Doc], size: int = 800, overlap: int = 100) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap)
    chunks = splitter.split_documents([to_document(d) for d in docs])
    counter: dict[str, int] = {}
    for c in chunks:
        i = counter.get(c.metadata["doc_id"], 0)
        c.metadata["chunk_index"] = i
        counter[c.metadata["doc_id"]] = i + 1
    return chunks


def main():
    docs = load_markdown("data/notes") + load_pdfs("data/pdfs")
    print(f"documents: {len(docs)}")

    for size in (500, 800, 1200):
        chunks = chunk_docs(docs, size=size, overlap=100)
        avg = sum(len(c.page_content) for c in chunks) / len(chunks)
        print(f"size {size}: {len(chunks)} chunks, average {avg:.0f} characters")

    chunks = chunk_docs(docs)  # default 800
    print("\nchunks per kind (size 800):")
    for kind, n in Counter(c.metadata["kind"] for c in chunks).items():
        print(f"  {kind}: {n}")

    shown = set()
    for c in chunks:
        kind = c.metadata["kind"]
        if kind not in shown and c.metadata["chunk_index"] == 1:
            shown.add(kind)
            print(f"\n[{kind}] {c.metadata['title']} chunk {c.metadata['chunk_index']}")
            print(c.page_content[:200])


if __name__ == "__main__":
    main()
