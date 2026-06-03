import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.models.user import User
from app.services.auth_service import AuthService

WEAK_PASSWORDS = ("admin", "admin123", "password", "12345678")


async def main():
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    force = "--force" in sys.argv
    admin_username = os.environ.get("ADMIN_USERNAME", "admin")
    new_password = os.environ.get("ADMIN_PASSWORD", "Admin@2024")

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.username == admin_username)
        )
        user = result.scalar_one_or_none()

        if not user:
            print(f"ERROR: User '{admin_username}' not found")
            await engine.dispose()
            sys.exit(1)

        if force:
            user.hashed_password = AuthService.hash_password(new_password)
            await session.commit()
            print(f"Admin password force-reset to env ADMIN_PASSWORD (default: Admin@2024)")
        else:
            is_weak = any(
                AuthService.verify_password(weak, user.hashed_password)
                for weak in WEAK_PASSWORDS
            )
            if is_weak:
                user.hashed_password = AuthService.hash_password(new_password)
                await session.commit()
                print(f"Admin password was a known weak default. Reset to env ADMIN_PASSWORD (default: Admin@2024)")
            else:
                print(f"Admin password has been manually changed. Skipping. Use --force to force reset.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
