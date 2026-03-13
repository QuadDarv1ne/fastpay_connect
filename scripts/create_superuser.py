"""
Script to create initial superuser for FastPay Connect.

Usage:
    python scripts/create_superuser.py

Or with custom credentials:
    python scripts/create_superuser.py --username admin --email admin@example.com --password SecurePass123!
"""

import argparse
import sys
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.utils.security import get_password_hash


def create_superuser(
    username: str = "admin",
    email: str = "admin@example.com",
    password: str = "ChangeMe123!",
) -> None:
    """Создание суперпользователя."""
    print(f"Creating superuser: {username}")
    print(f"Email: {email}")
    print("-" * 50)

    db = SessionLocal()
    repo = UserRepository(db)

    try:
        # Проверка существования пользователя
        existing_user = repo.get_by_username(username)
        if existing_user:
            print(f"❌ User '{username}' already exists!")
            return

        existing_email = repo.get_by_email(email)
        if existing_email:
            print(f"❌ Email '{email}' already registered!")
            return

        # Создание суперпользователя
        user = repo.create(
            username=username,
            email=email,
            password=password,
            is_active=True,
            is_superuser=True,
            roles=["admin"],
        )

        if user:
            print(f"✅ Superuser '{username}' created successfully!")
            print("-" * 50)
            print(f"ID: {user.id}")
            print(f"Username: {user.username}")
            print(f"Email: {user.email}")
            print(f"Roles: {user.get_roles()}")
            print(f"Is Superuser: {user.is_superuser}")
            print("-" * 50)
            print("\n📝 Next steps:")
            print("   1. Change the default password!")
            print("   2. Login: POST /api/auth/login")
            print("   3. Use the access token for admin endpoints")
            print("\n🔐 Example login:")
            print(f"   curl -X POST 'http://localhost:8080/api/auth/login' \\")
            print(f"     -H 'Content-Type: application/x-www-form-urlencoded' \\")
            print(f"     -d 'username={username}&password={password}'")
        else:
            print("❌ Failed to create user (username/email may already exist)")

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Create superuser for FastPay Connect")
    parser.add_argument(
        "--username",
        type=str,
        default="admin",
        help="Username (default: admin)",
    )
    parser.add_argument(
        "--email",
        type=str,
        default="admin@example.com",
        help="Email (default: admin@example.com)",
    )
    parser.add_argument(
        "--password",
        type=str,
        default="ChangeMe123!",
        help="Password (default: ChangeMe123!)",
    )

    args = parser.parse_args()

    # Валидация пароля
    if len(args.password) < 8:
        print("❌ Password must be at least 8 characters long")
        sys.exit(1)

    create_superuser(
        username=args.username,
        email=args.email,
        password=args.password,
    )


if __name__ == "__main__":
    main()
