from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.database import get_session
from app.core.deps import get_current_user
from app.domain.models import Doubt, User
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/v1/doubts", tags=["Doubts"])

@router.post("/")
async def create_doubt(
    title: str = Form(...),
    content: str = Form(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    doubt = Doubt(id=str(uuid.uuid4()), user_id=current_user.id, title=title, content=content, created_at=datetime.utcnow())
    session.add(doubt)
    await session.commit()
    return {"message": "Doubt posted", "doubt_id": doubt.id}

@router.get("/")
async def list_doubts(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Doubt).order_by(Doubt.created_at.desc()))
    doubts = result.scalars().all()
    out = [
        {
            "id": d.id,
            "user_id": d.user_id,
            "title": d.title,
            "content": d.content,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "resolved": d.resolved,
        }
        for d in doubts
    ]
    return {"doubts": out}
