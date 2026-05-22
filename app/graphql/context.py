"""GraphQL context and authentication utilities."""

from typing import Any, Callable, Dict, Generator, Optional
from fastapi import Request

# Overridable DB session getter for testing
_db_session_factory: Optional[Callable[[], Generator]] = None


def set_db_session_factory(factory: Optional[Callable[[], Generator]]) -> None:
    """Set a custom DB session factory for testing."""
    global _db_session_factory
    _db_session_factory = factory


def _get_db_session():
    """Get DB session from overridden factory or default SessionLocal."""
    if _db_session_factory is not None:
        return next(_db_session_factory())
    from app.database import SessionLocal
    return SessionLocal()


async def get_graphql_context(request: Request) -> Dict[str, Any]:
    """Build GraphQL context dict with authenticated user info."""
    from app.utils.security import decode_token
    from app.utils.token_blacklist import is_token_blacklisted

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]

        # Check if token is blacklisted
        if not is_token_blacklisted(token):
            # Decode and validate token
            token_data = decode_token(token, expected_type="access")
            if token_data:
                # Verify user still exists and is active
                db = _get_db_session()
                try:
                    from app.models.user import User
                    user = db.query(User).filter(User.id == token_data.user_id).first()
                    if user and user.is_active:
                        roles = user.get_roles()
                        return {
                            "user_id": user.id,
                            "user_roles": roles,
                            "is_admin": "admin" in roles or user.is_superuser,
                        }
                finally:
                    db.close()

    # Unauthenticated context
    return {"user_id": None, "user_roles": None, "is_admin": False}
