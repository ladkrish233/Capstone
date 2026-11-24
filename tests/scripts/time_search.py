import time

from dotenv import load_dotenv

load_dotenv()
from rag.remote_embed import RemoteEmbeddings
from rag.store import search

emb = RemoteEmbeddings()
for run in (1, 2, 3):
    t0 = time.perf_counter()
    emb.embed_query("what is my mom's birthday")
    t1 = time.perf_counter()
    search("what is my mom's birthday", k=4)
    t2 = time.perf_counter()
    print(f"run {run}: embed only={t1 - t0:.1f}s   embed+db={t2 - t1:.1f}s")