"""
Repository for user operations.
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Optional, List
from datetime import datetime, timezone
import logging
import json

from app.models.user import User
from app.utils.security import get_password_hash

logger = logging.getLogger(__name__)


class UserRepository:
    """Репозиторий для работы с пользователями."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Получить пользователя по ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Получить пользователя по username."""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Получить пользователя по email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
    ) -> List[User]:
        """Получить всех пользователей с пагинацией."""
        query = self.db.query(User)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        return query.offset(skip).limit(limit).all()
    
    def get_count(self, is_active: Optional[bool] = None) -> int:
        """Получить количество пользователей."""
        query = self.db.query(User)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        return query.count()
    
    def create(
        self,
        username: str,
        email: str,
        password: str,
        is_active: bool = True,
        is_superuser: bool = False,
        roles: Optional[List[str]] = None,
    ) -> Optional[User]:
        """Создать нового пользователя."""
        try:
            # Проверка на существование
            if self.get_by_username(username):
                logger.warning(f"User with username '{username}' already exists")
                return None
            
            if self.get_by_email(email):
                logger.warning(f"User with email '{email}' already exists")
                return None
            
            hashed_password = get_password_hash(password)
            
            user = User(
                username=username,
                email=email,
                hashed_password=hashed_password,
                is_active=is_active,
                is_superuser=is_superuser,
                roles=json.dumps(roles) if roles else json.dumps(["viewer"]),
            )
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"User '{username}' created successfully")
            return user
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error creating user: {e}")
            return None
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating user: {e}")
            return None
    
    def update(
        self,
        user: User,
        username: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_superuser: Optional[bool] = None,
        roles: Optional[List[str]] = None,
    ) -> Optional[User]:
        """Обновить данные пользователя."""
        try:
            if username is not None:
                # Проверка на дубликат username
                existing = self.get_by_username(username)
                if existing and existing.id != user.id:
                    logger.warning(f"Username '{username}' already taken")
                    return None
                user.username = username
            
            if email is not None:
                # Проверка на дубликат email
                existing = self.get_by_email(email)
                if existing and existing.id != user.id:
                    logger.warning(f"Email '{email}' already taken")
                    return None
                user.email = email
            
            if password is not None:
                user.hashed_password = get_password_hash(password)
            
            if is_active is not None:
                user.is_active = is_active
            
            if is_superuser is not None:
                user.is_superuser = is_superuser
            
            if roles is not None:
                user.roles = json.dumps(roles)
            
            user.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"User '{user.username}' updated successfully")
            return user
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error updating user: {e}")
            return None
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating user: {e}")
            return None
    
    def delete(self, user: User) -> bool:
        """Удалить пользователя."""
        try:
            self.db.delete(user)
            self.db.commit()
            logger.info(f"User '{user.username}' deleted successfully")
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deleting user: {e}")
            return False
    
    def update_last_login(self, user: User) -> User:
        """Обновить время последнего входа."""
        user.last_login = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def get_users_by_role(self, role: str) -> List[User]:
        """Получить пользователей с указанной ролью."""
        users = self.db.query(User).filter(User.is_active == True).all()
        return [user for user in users if user.has_role(role)]
