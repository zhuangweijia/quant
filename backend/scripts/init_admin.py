import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.user import User
from app.services.auth_service import AuthService


async def main():
    database_url = os.environ.get("DATABASE_URL", "")
    admin_username = os.environ.get("ADMIN_USERNAME", "admin")
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@2024")

    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        result = await session.execute(select(User).where(User.username == admin_username))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Admin user '{admin_username}' already exists, skipping.")
        else:
            hashed = AuthService.hash_password(admin_password)
            user = User(
                username=admin_username,
                hashed_password=hashed,
                role="admin",
                is_active=True,
            )
            session.add(user)
            await session.commit()
            print(f"Admin user '{admin_username}' created successfully.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
