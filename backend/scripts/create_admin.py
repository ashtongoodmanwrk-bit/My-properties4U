import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.security import hash_password


def main():
    email, password = sys.argv[1].lower(), sys.argv[2]
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            print("A user with that email already exists")
            return
        db.add(
            User(
                email=email,
                password_hash=hash_password(password),
                full_name="Admin",
                role="admin",
            )
        )
        db.commit()
    print(f"Admin created: {email}")


main()
