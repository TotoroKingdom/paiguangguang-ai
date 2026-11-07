import argparse
import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal, init_db
from app.modules.identity.models import AdminUser
from app.repositories import utc_now


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update an administrator")
    parser.add_argument("--username", default="admin", help="Administrator username")
    args = parser.parse_args()

    password = getpass.getpass("Administrator password (minimum 12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters")

    init_db()
    with SessionLocal() as session:
        user = session.scalar(select(AdminUser).where(AdminUser.username == args.username))
        now = utc_now()
        if user is None:
            session.add(
                AdminUser(
                    username=args.username,
                    password_hash=hash_password(password),
                    role="admin",
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            user.password_hash = hash_password(password)
            user.role = "admin"
            user.is_active = True
            user.updated_at = now
        session.commit()
        print(f"Administrator '{args.username}' is ready.")


if __name__ == "__main__":
    main()
