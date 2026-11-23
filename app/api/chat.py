from fastapi import APIRouter,Header,HTTPException,Request
from app.models import ChatRequest,ChatResponse
from app.security import check_key
import logging

logger=logging.getLogger(__name__)
router=APIRouter()


@router.post("/chat",response_model=ChatResponse)
async def chat(request:Request,req:ChatRequest,x_api_key: str | None = Header(default=None)):
    check_key(x_api_key,"API_KEY")
    try:
        result=await request.app.state.brain.ask(req.message)
    except Exception :
        logger.exception("agent failed")
        raise HTTPException(status_code=502,detail="agent unavailabe")
    return ChatResponse(answer=result.output)

