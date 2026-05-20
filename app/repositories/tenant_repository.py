"""
Repository for tenant operations.
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Optional, List
import logging
import json
import secrets

from app.models.tenant import Tenant, TenantStatus

logger = logging.getLogger(__name__)


class TenantRepository:
    """Репозиторий для работы с tenant'ами."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, tenant_id: int) -> Optional[Tenant]:
        """Получить tenant по ID."""
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        """Получить tenant по slug."""
        return self.db.query(Tenant).filter(Tenant.slug == slug).first()

    def get_by_api_key(self, api_key: str) -> Optional[Tenant]:
        """Получить tenant по API ключу."""
        return self.db.query(Tenant).filter(Tenant.api_key == api_key).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> List[Tenant]:
        """Получить все tenant'ы с пагинацией."""
        query = self.db.query(Tenant)

        if status:
            query = query.filter(Tenant.status == status)

        return query.offset(skip).limit(limit).all()

    def get_count(self, status: Optional[str] = None) -> int:
        """Получить количество tenant'ов."""
        query = self.db.query(Tenant)

        if status:
            query = query.filter(Tenant.status == status)

        return query.count()

    def create(
        self,
        name: str,
        slug: str,
        description: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        allowed_gateways: Optional[List[str]] = None,
        api_key: Optional[str] = None,
    ) -> Optional[Tenant]:
        """Создать новый tenant."""
        try:
            # Проверка на существование slug
            if self.get_by_slug(slug):
                logger.warning(f"Tenant with slug '{slug}' already exists")
                return None

            # Генерируем API ключ если не указан
            if not api_key:
                api_key = secrets.token_urlsafe(32)

            tenant = Tenant(
                name=name,
                slug=slug,
                api_key=api_key,
                description=description,
                contact_email=contact_email,
                contact_phone=contact_phone,
                allowed_payment_gateways=json.dumps(allowed_gateways) if allowed_gateways else None,
                status=TenantStatus.ACTIVE.value,
            )

            self.db.add(tenant)
            self.db.commit()
            self.db.refresh(tenant)

            logger.info(f"Tenant '{name}' created successfully with slug '{slug}'")
            return tenant

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error creating tenant: {e}")
            return None
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating tenant: {e}")
            return None

    def update(
        self,
        tenant: Tenant,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        status: Optional[str] = None,
        allowed_gateways: Optional[List[str]] = None,
        settings: Optional[dict] = None,
    ) -> Optional[Tenant]:
        """Обновить данные tenant."""
        try:
            if name is not None:
                tenant.name = name

            if slug is not None:
                # Проверка на дубликат slug
                existing = self.get_by_slug(slug)
                if existing and existing.id != tenant.id:
                    logger.warning(f"Slug '{slug}' already taken")
                    return None
                tenant.slug = slug

            if description is not None:
                tenant.description = description

            if contact_email is not None:
                tenant.contact_email = contact_email

            if contact_phone is not None:
                tenant.contact_phone = contact_phone

            if status is not None:
                tenant.status = status

            if allowed_gateways is not None:
                tenant.allowed_payment_gateways = json.dumps(allowed_gateways)

            if settings is not None:
                tenant.settings_json = json.dumps(settings)

            from datetime import datetime, timezone
            tenant.updated_at = datetime.now(timezone.utc)

            self.db.commit()
            self.db.refresh(tenant)

            logger.info(f"Tenant '{tenant.name}' updated successfully")
            return tenant

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error updating tenant: {e}")
            return None
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating tenant: {e}")
            return None

    def delete(self, tenant: Tenant) -> bool:
        """Удалить tenant."""
        try:
            self.db.delete(tenant)
            self.db.commit()
            logger.info(f"Tenant '{tenant.name}' deleted successfully")
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deleting tenant: {e}")
            return False

    def regenerate_api_key(self, tenant: Tenant) -> Optional[str]:
        """Сгенерировать новый API ключ."""
        try:
            new_api_key = secrets.token_urlsafe(32)
            tenant.api_key = new_api_key
            self.db.commit()
            self.db.refresh(tenant)
            logger.info(f"API key regenerated for tenant '{tenant.name}'")
            return new_api_key
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error regenerating API key: {e}")
            return None

    def get_by_status(self, status: str) -> List[Tenant]:
        """Получить tenant'ы по статусу."""
        return self.db.query(Tenant).filter(Tenant.status == status).all()
