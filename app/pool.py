import os 
from urllib.parse import parse_qsl,urlencode,urlsplit,urlunsplit
import asyncpg

_PSYCOPG_ONLY = {"channel_binding", "options"}

def asyncpg_dsn(url:str):
    parts=urlsplit(url)
    keep = [(k,v) for k , v in parse_qsl(parts.query) if k not in _PSYCOPG_ONLY]
    return urlunsplit(parts._replace(query=urlencode(keep)))

async def make_pool(url:str|None=None)->asyncpg.Pool:
    dsn = asyncpg_dsn(url or os.environ["DATABASE_URL"])
    return await asyncpg.create_pool(
        dsn,
        min_size=1,
        max_size=5,
        timeout=30,
        max_inactive_connection_lifetime=60,
        statement_cache_size=0
    )