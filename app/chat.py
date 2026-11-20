from fastapi import APIRouter,HTTPException,Header
from models import ChatResponse,ChatRequest
from app.security import check_key

router=APIRouter()

@router.post("/chat",response_model=ChatResponse)
async def chat(req:ChatRequest,x_api_key: str | None = Header(default=None)):
    check_key(x_api_key,"API_KEY")
    try:
        result=await agent.run(req.message)
    except Exception :
        logger.exception("agent failed")
        raise HTTPException(status_code=502,detail="agent unavailabe")
    return ChatResponse(answer=result.output)

