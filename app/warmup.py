from fastapi import Header,HTTPException,APIRouter
from app.security import check_key


router = APIRouter()

@router.get()