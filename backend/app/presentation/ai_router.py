from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_session
from app.application.ai_service import AIMatchingService
from app.core.deps import get_current_user
from app.domain.models import User

router = APIRouter(prefix="/api/v1/ai", tags=["Artificial Intelligence"])

@router.post("/update-profile-embeddings")
async def update_embeddings(
    skills: str = Form(...),
    goals: str = Form(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = AIMatchingService(session)
    try:
        return await service.update_embeddings(current_user.id, skills, goals)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/find-mentors")
async def find_mentors(query: str, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    service = AIMatchingService(session)
    return await service.find_mentors(query)