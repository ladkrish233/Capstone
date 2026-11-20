import os

import requests
from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings

load_dotenv()

URL = os.environ["EMBED_URL"].rstrip("/")
if not URL.endswith("/embed"):
    URL += "/embed"
KEY = os.environ["EMBED_KEY"]
GROUP = 8  # texts per request, below the server limit of 16


def _post(texts: list[str], kind: str) -> list[list[float]]:
    r = requests.post(
        URL,
        json={"texts": texts, "kind": kind},
        headers={"X-Embed-Key": KEY},
        timeout=60,  # the first call after idle can take about 10 s
    )
    r.raise_for_status()
    return r.json()["embeddings"]


class RemoteEmbeddings(Embeddings):
    def embed_query(self, text: str) -> list[float]:
        return _post([text], "query")[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), GROUP):
            vectors.extend(_post(texts[i : i + GROUP], "document"))
        return vectors


if __name__ == "__main__":
    v = RemoteEmbeddings().embed_query("chai kaise banate hain")
    print("dim:", len(v))