"""
2FA (Two-Factor Authentication) routes.
Автор: Dupley Maxim Igorevich
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    MFASetupRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    MFADisableRequest,
    MFAStatusResponse,
    LoginResponse,
)
from app.services.mfa_service import mfa_service
from app.utils.security import verify_password, get_password_hash
from datetime import datetime, timezone

router = APIRouter(prefix="/mfa", tags=["2FA", "Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Получить текущего пользователя из токена."""
    from jose import JWTError, jwt
    from app.utils.security import SECRET_KEY, ALGORITHM
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    
    return user


@router.post("/setup", response_model=MFASetupResponse)
async def setup_mfa(
    request: MFASetupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Настройка 2FA для текущего пользователя.
    
    Требуется ввести пароль для подтверждения.
    Возвращает секрет и QR код для настройки в Google Authenticator.
    """
    # Проверяем пароль
    if not verify_password(request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password"
        )
    
    # Проверяем, не включен ли уже 2FA
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled"
        )
    
    # Генерируем секрет и backup коды
    secret, qr_code_url, backup_codes = mfa_service.setup_mfa(current_user.email)
    
    # Сохраняем секрет временно (до подтверждения)
    current_user.mfa_secret = secret
    db.commit()
    
    return MFASetupResponse(
        secret=secret,
        qr_code_url=qr_code_url,
        backup_codes=backup_codes,
        message="Scan QR code with Google Authenticator and verify code"
    )


@router.post("/verify")
async def verify_mfa(
    request: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Подтверждение включения 2FA.
    
    После сканирования QR кода введите код из приложения.
    """
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup not initiated. Call /mfa/setup first."
        )
    
    # Проверяем код
    if not mfa_service.verify_code(current_user.mfa_secret, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Генерируем и хешируем backup коды
    backup_codes = mfa_service.generate_backup_codes()
    hashed_codes = mfa_service.hash_backup_codes(backup_codes)
    
    # Включаем 2FA
    current_user.mfa_enabled = True
    current_user.mfa_backup_codes = mfa_service.serialize_backup_codes(hashed_codes)
    current_user.mfa_last_verified = datetime.now(timezone.utc)
    db.commit()
    
    return {
        "message": "2FA enabled successfully",
        "backup_codes": backup_codes,  # Показываем только один раз!
        "warning": "Save these backup codes in a secure location. They won't be shown again!"
    }


@router.post("/disable")
async def disable_mfa(
    request: MFADisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Отключение 2FA.
    
    Требуется пароль и текущий TOTP код.
    """
    # Проверяем пароль
    if not verify_password(request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password"
        )
    
    # Проверяем, включен ли 2FA
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled"
        )
    
    # Проверяем код (сначала TOTP, потом backup)
    verified = False
    
    # Пробуем TOTP код
    if current_user.mfa_secret and mfa_service.verify_code(current_user.mfa_secret, request.code):
        verified = True
    
    # Если не подошло, пробуем backup код
    if not verified and current_user.mfa_backup_codes:
        hashed_codes = mfa_service.deserialize_backup_codes(current_user.mfa_backup_codes)
        if mfa_service.verify_backup_code(request.code, hashed_codes):
            verified = True
            # Удаляем использованный backup код
            new_codes = mfa_service.remove_used_backup_code(request.code, hashed_codes)
            current_user.mfa_backup_codes = mfa_service.serialize_backup_codes(new_codes)
    
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Отключаем 2FA
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    current_user.mfa_backup_codes = None
    current_user.mfa_last_verified = None
    db.commit()
    
    return {"message": "2FA disabled successfully"}


@router.get("/status", response_model=MFAStatusResponse)
async def get_mfa_status(
    current_user: User = Depends(get_current_user)
):
    """Получить статус 2FA текущего пользователя."""
    return MFAStatusResponse(
        enabled=current_user.mfa_enabled,
        backup_codes_remaining=current_user.get_backup_codes_count(),
        last_verified=current_user.mfa_last_verified
    )


@router.post("/backup-codes")
async def regenerate_backup_codes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Генерация новых backup кодов.
    
    Старые коды будут аннулированы.
    """
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled"
        )
    
    # Генерируем новые коды
    backup_codes = mfa_service.generate_backup_codes()
    hashed_codes = mfa_service.hash_backup_codes(backup_codes)
    
    # Сохраняем
    current_user.mfa_backup_codes = mfa_service.serialize_backup_codes(hashed_codes)
    db.commit()
    
    return {
        "message": "New backup codes generated",
        "backup_codes": backup_codes,
        "warning": "Save these backup codes. Old codes are no longer valid!"
    }
