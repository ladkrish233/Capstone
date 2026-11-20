import os
import secrets

from fastapi import HTTPException


def check_key(given:str | None ,env_name:str):
    expected=os.environ.get(env_name,"")
    if not expected or not secrets.compare_digest((given or "").encode(),expected.encode()):
        raise HTTPException(status_code=401,detail="unauthorized")