import os
from contextlib import asynccontextmanager
from typing import Literal

from embed_local import LocalEmbeddings
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

EMBED_KEY=os.environ["EMBED_KEY"]
state:dict = {}

@asynccontextmanager
async def lifeapp(app:FastAPI):
    state["model"]=LocalEmbeddings()
    yield

app=FastAPI(lifespan=lifeapp)

class EmbedRequest(BaseModel):
    texts:list[str]=Field(min_length=1,max_length=16)
    kind:Literal["query", "document"] = "document"


@app.get("/health")
def health():
    return{"ok" : "model" in state}

@app.post("/embed")
def embed(req: EmbedRequest, x_embed_key: str = Header(default="")):
    if x_embed_key != EMBED_KEY:
        raise HTTPException(status_code=401, detail="bad key")
    if any(len(t) >2000 for t in req.texts):
        raise HTTPException(status_code=413,detail="text too long")
    vectors=state["model"].embed(req.texts,req.kind)
    return {"embeddings": vectors, "dims": 768}