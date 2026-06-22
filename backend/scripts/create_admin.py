"""Seed an initial admin user. Idempotent: skips if the email already exists.

Run inside the backend container:
    docker compose exec backend python -m scripts.create_admin
"""
import asyncio

from app.core.security import hash_password
from app.database import async_session
from app.models.enums import UserRole
from app.models.user import User
from app.services import user_service

ADMIN_EMAIL = "admin@somnolence.com"
ADMIN_PASSWORD = "admin123"
ADMIN_NAME = "Administrator"


async def main() -> None:
    async with async_session() as db:
        existing = await user_service.get_user_by_email(db, ADMIN_EMAIL)
        if existing:
            print(f"[create_admin] User {ADMIN_EMAIL} already exists; nothing to do.")
            return

        user = User(
            email=ADMIN_EMAIL,
            hashed_password=hash_password(ADMIN_PASSWORD),
            full_name=ADMIN_NAME,
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        print(f"[create_admin] Admin created: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
