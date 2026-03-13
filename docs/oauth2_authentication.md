# OAuth2 Authentication for Admin Panel

## Обзор

FastPay Connect теперь поддерживает **OAuth2 аутентификацию** для защиты admin endpoints. Система использует JWT токены (JSON Web Tokens) для безопасной аутентификации и авторизации пользователей.

## Возможности

- ✅ **JWT токены** (access + refresh)
- ✅ **Ролевая модель** (admin, operator, viewer)
- ✅ **Хеширование паролей** (bcrypt)
- ✅ **Обновление токенов** без повторного логина
- ✅ **Rate limiting** для auth endpoints
- ✅ **Поддержка суперпользователей** (is_superuser)

## Роли пользователей

| Роль | Описание | Права |
|------|----------|-------|
| `admin` | Полный доступ | Все admin endpoints |
| `operator` | Оперативный доступ | Просмотр, возвраты, отмены |
| `viewer` | Только просмотр | Просмотр статистики и платежей |
| `superuser` | Техническая роль | Обходит все проверки ролей |

## Быстрый старт

### 1. Применение миграции БД

```bash
alembic upgrade head
```

### 2. Создание первого пользователя (superuser)

```python
# create_superuser.py
from app.database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.utils.security import get_password_hash

db = SessionLocal()
repo = UserRepository(db)

# Создание суперпользователя
user = repo.create(
    username="admin",
    email="admin@example.com",
    password="ChangeMe123!",  # Смените пароль!
    is_active=True,
    is_superuser=True,
    roles=["admin"],
)

if user:
    print(f"User '{user.username}' created successfully!")
else:
    print("Failed to create user (username/email may already exist)")

db.close()
```

```bash
python create_superuser.py
```

### 3. Получение токена

```bash
# Через form-data (OAuth2)
curl -X POST "http://localhost:8080/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=ChangeMe123!"

# Через JSON
curl -X POST "http://localhost:8080/api/auth/login/json" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"ChangeMe123!"}'
```

**Ответ:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 4. Использование токена

```bash
curl -X GET "http://localhost:8080/admin/payments/dashboard" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## API Endpoints

### Регистрация

```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "newuser",
  "email": "user@example.com",
  "password": "SecurePass123!",
  "roles": ["viewer"]
}
```

**Ответ:** `UserResponse`

### Login (OAuth2 form-data)

```http
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin&password=ChangeMe123!
```

**Ответ:** `Token`

### Login (JSON)

```http
POST /api/auth/login/json
Content-Type: application/json

{
  "username": "admin",
  "password": "ChangeMe123!"
}
```

**Ответ:** `Token`

### Обновление токена

```http
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Ответ:** `Token` (новые access и refresh токены)

### Информация о пользователе

```http
GET /api/auth/me
Authorization: Bearer <access_token>
```

**Ответ:** `UserResponse`

### Смена пароля

```http
POST /api/auth/change-password
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "old_password": "OldPass123!",
  "new_password": "NewSecurePass456!"
}
```

**Ответ:** `{"status": "success", "message": "Password changed successfully"}`

### Logout

```http
POST /api/auth/logout
Authorization: Bearer <access_token>
```

**Ответ:** `{"status": "success", "message": "Logged out successfully"}`

## Интеграция с Admin endpoints

Все admin endpoints теперь требуют OAuth2 аутентификации:

```python
from app.utils.security import get_current_user, require_any_role
from app.models.user import User

# Базовая защита (любой авторизованный пользователь)
async def get_endpoint(
    current_user: User = Depends(get_current_user),
):
    ...

# Требуется конкретная роль
async def admin_endpoint(
    current_user: User = Depends(require_any_role(["admin"])),
):
    ...

# Требуется одна из ролей
async def operator_endpoint(
    current_user: User = Depends(require_any_role(["admin", "operator"])),
):
    ...
```

## Конфигурация

### Переменные окружения

```env
# Секретный ключ для JWT (минимум 32 символа!)
SECRET_KEY=your-super-secret-key-min-32-characters-long!

# Время жизни токенов (в минутах/днях)
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Настройки по умолчанию

| Параметр | Значение | Описание |
|----------|----------|----------|
| `ALGORITHM` | HS256 | Алгоритм подписи JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 60 | Время жизни access токена |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Время жизни refresh токена |

## Структура JWT токена

```json
{
  "sub": "username",
  "user_id": 1,
  "roles": ["admin", "operator"],
  "exp": 1710364800,
  "type": "access"
}
```

**Поля:**
- `sub` - username пользователя
- `user_id` - ID пользователя в БД
- `roles` - список ролей
- `exp` - timestamp истечения токена
- `type` - тип токена (access/refresh)

## Безопасность

### Требования к паролю

- Минимум 8 символов
- Рекомендуется использовать буквы, цифры и специальные символы

### Rate Limiting

| Endpoint | Лимит |
|----------|-------|
| `/api/auth/register` | 10/час |
| `/api/auth/login` | 20/минуту |
| `/api/auth/login/json` | 20/минуту |
| `/api/auth/refresh` | 30/час |
| `/api/auth/change-password` | 10/час |

### Рекомендации для production

1. **Смените SECRET_KEY** на уникальный (минимум 32 символа)
2. **Используйте HTTPS** для передачи токенов
3. **Храните токены безопасно** (httpOnly cookies, secure storage)
4. **Реализуйте blacklist** для отозванных токенов
5. **Мониторьте логины** и подозрительную активность

## Примеры использования

### Python (httpx)

```python
import httpx

async def authenticate_and_get_dashboard():
    async with httpx.AsyncClient() as client:
        # Login
        response = await client.post(
            "http://localhost:8080/api/auth/login",
            data={"username": "admin", "password": "ChangeMe123!"}
        )
        tokens = response.json()
        access_token = tokens["access_token"]
        
        # Получение дашборда
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.get(
            "http://localhost:8080/admin/payments/dashboard",
            headers=headers
        )
        
        return response.json()
```

### JavaScript (fetch)

```javascript
async function loginAndGetDashboard() {
    // Login
    const loginResponse = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'username=admin&password=ChangeMe123!'
    });
    
    const tokens = await loginResponse.json();
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
    
    // Получение дашборда
    const dashboardResponse = await fetch('/admin/payments/dashboard', {
        headers: { 'Authorization': `Bearer ${tokens.access_token}` }
    });
    
    return await dashboardResponse.json();
}
```

### cURL

```bash
# Сохранение токена в переменную
TOKEN=$(curl -s -X POST "http://localhost:8080/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=ChangeMe123!" \
  | jq -r '.access_token')

# Использование токена
curl -X GET "http://localhost:8080/admin/payments/dashboard" \
  -H "Authorization: Bearer $TOKEN"
```

## Troubleshooting

### Ошибка: "Could not validate credentials"

- Токен истёк или недействителен
- Используйте refresh token для получения нового access токена

### Ошибка: "User account is disabled"

- Пользователь был деактивирован администратором
- Обратитесь к суперпользователю

### Ошибка: "Not enough permissions"

- У пользователя недостаточно прав для доступа к endpoint
- Требуется роль admin/superuser

### Ошибка: "Incorrect username or password"

- Проверьте учётные данные
- Убедитесь, что пользователь существует

## Миграция с API Key

Если вы использовали API Key для аутентификации:

1. Создайте пользователей через OAuth2
2. Обновите клиенты для использования JWT токенов
3. Отключите проверку API Key в admin routes
4. Протестируйте новые endpoints
5. Удалите старый код аутентификации

## Дополнительные ресурсы

- [JWT.io](https://jwt.io/) - декодер JWT токенов
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/) - документация FastAPI
- [python-jose](https://python-jose.readthedocs.io/) - библиотека для работы с JWT
