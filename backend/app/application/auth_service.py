from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.models import User, UserProfile
from app.core.security import verify_password, get_password_hash, create_access_token
import uuid
from datetime import datetime, timedelta

class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(self, email: str, password: str, full_name: str, role: str = "STUDENT"):
        result = await self.session.execute(select(User).where(User.email == email))
        if result.scalars().first():
            raise ValueError("Email already exists")
        
        user_id = str(uuid.uuid4())
        user = User(id=user_id, email=email, password_hash=get_password_hash(password), role=role, failed_attempts=0)
        profile = UserProfile(user_id=user_id, full_name=full_name, skills=[], goals=[])
        
        self.session.add(user)
        self.session.add(profile)
        await self.session.commit()
        
        token = create_access_token({"sub": user_id})
        return {"access_token": token, "token_type": "bearer", "user_id": user_id, "full_name": full_name, "role": role}

    async def login(self, email: str, password: str):
        result = await self.session.execute(select(User).where(User.email == email))
        user = result.scalars().first()

        if not user:
            # avoid leaking existence
            raise ValueError("Invalid credentials")

        # check lock
        if getattr(user, 'locked_until', None):
            if datetime.utcnow() < user.locked_until:
                raise ValueError(f"Account locked until {user.locked_until.isoformat()} UTC")
            else:
                user.failed_attempts = 0
                user.locked_until = None
                self.session.add(user)
                await self.session.commit()

        if not verify_password(password, user.password_hash):
            # increment failed attempts
            fa = getattr(user, 'failed_attempts', 0) + 1
            user.failed_attempts = fa
            if fa >= 5:
                # lock for 15 minutes
                user.locked_until = datetime.utcnow() + timedelta(minutes=15)
            self.session.add(user)
            await self.session.commit()
            remaining = max(0, 5 - fa)
            if getattr(user, 'locked_until', None):
                raise ValueError(f"Account locked due to too many attempts. Try again later.")
            raise ValueError(f"Invalid credentials. {remaining} attempts left.")
        
        profile_res = await self.session.execute(select(UserProfile).where(UserProfile.user_id == user.id))
        profile = profile_res.scalars().first()
        
        # successful login -> reset counters
        user.failed_attempts = 0
        user.locked_until = None
        self.session.add(user)
        await self.session.commit()

        token = create_access_token({"sub": user.id})
        return {"access_token": token, "token_type": "bearer", "user_id": user.id, "full_name": profile.full_name if profile else "User", "role": user.role}