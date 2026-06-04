from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.models import UserProfile
from app.infrastructure.vecter_db import mentor_collection
import hashlib
from typing import List

class AIMatchingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _get_mock_vector(self, text: str) -> List[float]:
        # Deterministic mock vector for guaranteed execution without OpenAI Key
        hash_obj = hashlib.sha256(text.encode()).hexdigest()
        return [float(int(hash_obj[i:i+2], 16))/255 for i in range(0, len(hash_obj), 2)][:384]

    async def update_embeddings(self, user_id: str, skills: str, goals: str):
        skills_list = [s.strip() for s in skills.split(',')]
        goals_list = [g.strip() for g in goals.split(',')]
        
        result = await self.session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = result.scalars().first()
        if not profile:
            raise ValueError("Profile not found")
            
        profile.skills = skills_list
        profile.goals = goals_list
        self.session.add(profile)
        await self.session.commit()
        
        text_to_embed = f"Skills: {skills}. Goals: {goals}."
        vector = self._get_mock_vector(text_to_embed)
        
        mentor_collection.upsert(
            ids=[user_id],
            embeddings=[vector],
            metadatas=[{"full_name": profile.full_name, "skills": skills}]
        )
        return {"message": "Profile updated and AI embeddings synced successfully"}

    async def find_mentors(self, query: str):
        query_vector = self._get_mock_vector(query)
        results = mentor_collection.query(query_embeddings=[query_vector], n_results=3)

        # If using the in-memory fallback, `results` is a simple list of dicts
        # Convert it to a Chromadb-like response shape expected by the frontend:
        # { "mentors": { "ids": [...], "metadatas": [[...]], "distances": [[...]] } }
        if isinstance(results, list):
            ids = [r.get('id') for r in results]
            metadatas = [[r.get('metadata', {}) for r in results]]
            scores = [r.get('score', 0) for r in results]
            max_score = max(scores) if scores else 0
            if max_score > 0:
                distances = [[1 - (s / max_score) for s in scores]]
            else:
                distances = [[1 for _ in scores]]

            return {"mentors": {"ids": ids, "metadatas": metadatas, "distances": distances}}

        # Otherwise assume the collection returned chromadb-compatible output
        return {"mentors": results}