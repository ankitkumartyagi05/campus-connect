from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_session
from app.core.deps import get_current_user
from app.domain.models import User
from sqlalchemy import select
from app.domain.models import UserProfile

router = APIRouter(prefix="/api/v1/users", tags=["Users"])

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = result.scalars().first()
    return {
        "email": current_user.email, 
        "role": current_user.role, 
        "profile": {
            "full_name": profile.full_name if profile else "User",
            "skills": profile.skills if profile else [],
            "goals": profile.goals if profile else [],
        }
    }