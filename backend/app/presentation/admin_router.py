from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_session
from app.core.deps import get_current_user
from app.domain.models import User, Doubt
from sqlalchemy import select, update, delete

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


def assert_admin(user: User):
    if user.role != 'ADMIN':
        raise HTTPException(status_code=403, detail='Admin privileges required')


@router.get('/users')
async def list_users(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    assert_admin(current_user)
    res = await session.execute(select(User))
    users = res.scalars().all()
    return [{ 'id': u.id, 'email': u.email, 'role': u.role, 'is_premium': getattr(u, 'is_premium', False) } for u in users]


@router.post('/users/{user_id}/role')
async def set_role(user_id: str, role: str = Form(...), current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    assert_admin(current_user)
    await session.execute(update(User).where(User.id == user_id).values(role=role))
    await session.commit()
    return {'ok': True}


@router.post('/users/{user_id}/premium')
async def set_premium(user_id: str, premium: bool = Form(True), current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    assert_admin(current_user)
    await session.execute(update(User).where(User.id == user_id).values(is_premium=premium))
    await session.commit()
    return {'ok': True}


@router.post('/users/{user_id}/unlock')
async def unlock_user(user_id: str, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    assert_admin(current_user)
    await session.execute(update(User).where(User.id == user_id).values(failed_attempts=0, locked_until=None))
    await session.commit()
    return {'ok': True}


@router.get('/doubts')
async def list_doubts(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    assert_admin(current_user)
    res = await session.execute(select(Doubt))
    doubts = res.scalars().all()
    return [ { 'id': d.id, 'title': d.title, 'content': d.content, 'user_id': d.user_id, 'resolved': d.resolved } for d in doubts ]


@router.delete('/doubts/{doubt_id}')
async def delete_doubt(doubt_id: str, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    assert_admin(current_user)
    await session.execute(delete(Doubt).where(Doubt.id == doubt_id))
    await session.commit()
    return {'ok': True}
