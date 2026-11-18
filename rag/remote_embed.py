import os

import requests
from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings

load_dotenv()

URL = os.environ["EMBED_URL"]


def _embed_one(text: str, kind: str) -> list[float]:
    r = requests.post(URL, json={"text": text, "kind": kind}, timeout=60)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict):
        data = data.get("embedding") or data.get("embeddings") or data.get("vector")

    return data


class RemoteEmbeddings(Embeddings):
    def embed_query(self, text: str) -> list[float]:
        return _embed_one(text, "query")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [_embed_one(t, "passage") for t in texts]


if __name__ == "__main__":
    v = RemoteEmbeddings().embed_query("chai kaise banate hain")
    print("dim:", v)
