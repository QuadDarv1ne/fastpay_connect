"""Tenant management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.tenant_repository import TenantRepository
from app.models.user import User
from app.utils.security import get_current_user
from app.middleware.rate_limiter import limiter
from app.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate

router = APIRouter(prefix="/tenants", tags=["Tenants"])


def get_tenant_repository(db: Session = Depends(get_db)) -> TenantRepository:
    """Dependency для получения TenantRepository."""
    return TenantRepository(db)


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def create_tenant(
    request: Request,
    tenant_data: TenantCreate,
    current_user: User = Depends(get_current_user),
    repository: TenantRepository = Depends(get_tenant_repository),
) -> TenantResponse:
    """Создать новый tenant (только superuser)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can create tenants",
        )

    tenant = repository.create(
        name=tenant_data.name,
        slug=tenant_data.slug,
        description=tenant_data.description,
        contact_email=tenant_data.contact_email,
        contact_phone=tenant_data.contact_phone,
        allowed_gateways=tenant_data.allowed_payment_gateways,
    )

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create tenant (slug may already exist)",
        )

    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        api_key=tenant.api_key,
        status=tenant.status,
        description=tenant.description,
        contact_email=tenant.contact_email,
        contact_phone=tenant.contact_phone,
        allowed_payment_gateways=tenant.get_allowed_gateways(),
        settings=tenant.get_settings(),
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )


@router.get("/", response_model=List[TenantResponse])
@limiter.limit("100/hour")
async def list_tenants(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    repository: TenantRepository = Depends(get_tenant_repository),
) -> List[TenantResponse]:
    """Получить список всех tenant'ов (только superuser)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can list tenants",
        )

    tenants = repository.get_all(skip=skip, limit=limit, status=status_filter)

    return [
        TenantResponse(
            id=t.id,
            name=t.name,
            slug=t.slug,
            api_key=t.api_key,
            status=t.status,
            description=t.description,
            contact_email=t.contact_email,
            contact_phone=t.contact_phone,
            allowed_payment_gateways=t.get_allowed_gateways(),
            settings=t.get_settings(),
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in tenants
    ]


@router.get("/{tenant_id}", response_model=TenantResponse)
@limiter.limit("100/hour")
async def get_tenant(
    request: Request,
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    repository: TenantRepository = Depends(get_tenant_repository),
) -> TenantResponse:
    """Получить tenant по ID."""
    tenant = repository.get_by_id(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Проверка прав доступа
    if not current_user.is_superuser:
        # Пользователь может видеть только свой tenant
        if hasattr(current_user, 'tenant_id') and current_user.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        api_key=tenant.api_key,
        status=tenant.status,
        description=tenant.description,
        contact_email=tenant.contact_email,
        contact_phone=tenant.contact_phone,
        allowed_payment_gateways=tenant.get_allowed_gateways(),
        settings=tenant.get_settings(),
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )


@router.put("/{tenant_id}", response_model=TenantResponse)
@limiter.limit("20/hour")
async def update_tenant(
    request: Request,
    tenant_id: int,
    tenant_data: TenantUpdate,
    current_user: User = Depends(get_current_user),
    repository: TenantRepository = Depends(get_tenant_repository),
) -> TenantResponse:
    """Обновить tenant."""
    tenant = repository.get_by_id(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Проверка прав доступа
    if not current_user.is_superuser:
        if hasattr(current_user, 'tenant_id') and current_user.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    updated = repository.update(
        tenant=tenant,
        name=tenant_data.name,
        slug=tenant_data.slug,
        description=tenant_data.description,
        contact_email=tenant_data.contact_email,
        contact_phone=tenant_data.contact_phone,
        status=tenant_data.status,
        allowed_gateways=tenant_data.allowed_payment_gateways,
        settings=tenant_data.settings,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tenant",
        )

    return TenantResponse(
        id=updated.id,
        name=updated.name,
        slug=updated.slug,
        api_key=updated.api_key,
        status=updated.status,
        description=updated.description,
        contact_email=updated.contact_email,
        contact_phone=updated.contact_phone,
        allowed_payment_gateways=updated.get_allowed_gateways(),
        settings=updated.get_settings(),
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/hour")
async def delete_tenant(
    request: Request,
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    repository: TenantRepository = Depends(get_tenant_repository),
) -> None:
    """Удалить tenant (только superuser)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can delete tenants",
        )

    tenant = repository.get_by_id(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    if not repository.delete(tenant):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tenant",
        )


@router.post("/{tenant_id}/regenerate-api-key", response_model=Dict[str, str])
@limiter.limit("5/hour")
async def regenerate_api_key(
    request: Request,
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    repository: TenantRepository = Depends(get_tenant_repository),
) -> Dict[str, str]:
    """Сгенерировать новый API ключ для tenant."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can regenerate API keys",
        )

    tenant = repository.get_by_id(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    new_key = repository.regenerate_api_key(tenant)

    if not new_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate API key",
        )

    return {"api_key": new_key}
