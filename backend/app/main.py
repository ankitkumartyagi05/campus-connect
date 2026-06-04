from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import Routers
from app.presentation.auth_router import router as auth_router
from app.presentation.user_router import router as user_router
from app.presentation.ai_router import router as ai_router
from app.presentation.ws_router import router as ws_router
from app.presentation.frontend_router import router as frontend_router
from app.presentation.doubts_router import router as doubts_router
from app.presentation.admin_router import router as admin_router

# Import DB for creation
from app.infrastructure.database import engine
from sqlmodel import SQLModel
from app.domain.models import User, UserProfile # Required for metadata creation
from app.infrastructure.database import AsyncSessionLocal
from app.core.security import get_password_hash
from sqlalchemy import select

app = FastAPI(title="CampusConnect API", version="1.0.0")

# Enterprise CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(ai_router)
app.include_router(ws_router)
app.include_router(frontend_router)
app.include_router(doubts_router)
app.include_router(admin_router)

# Serve Static Frontend Files (CSS/JS)
app.mount("/assets", StaticFiles(directory="."), name="assets")

@app.on_event("startup")
async def startup():
    # Create Database Tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    # Seed an admin user if missing
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.email == 'admin@campus.local'))
        admin = res.scalars().first()
        if not admin:
            admin_pw = 'AdminPass123!'
            admin_user = User(email='admin@campus.local', password_hash=get_password_hash(admin_pw), role='ADMIN', is_verified=True, is_premium=True)
            session.add(admin_user)
            await session.commit()
            print('Seeded admin user: admin@campus.local password:', admin_pw)