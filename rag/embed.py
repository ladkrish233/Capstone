import os

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

load_dotenv()

embedder = OpenAIEmbeddings(
    model="nvidia/nemotron-3-embed-1b:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
    check_embedding_ctx_length=False,
)


def embed_docments(chunks: list[Document]) -> list[list[float]]:
    text = [c.page_content for c in chunks]
    return embedder.embed_documents(text)


def embed_query(text: str) -> list[float]:
    return embedder.embed_query(text)
