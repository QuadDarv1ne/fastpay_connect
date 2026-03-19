# Инструкция по установке RuStore Pay SDK

## Содержание

1. [Подготовка](#подготовка)
2. [Серверная часть](#серверная-часть)
3. [Android часть](#android-часть)
4. [Webhook настройка](#webhook-настройка)
5. [Тестирование](#тестирование)

---

## Подготовка

### Получение учётных данных RuStore

1. Зарегистрируйтесь в [Консоли разработчика RuStore](https://console.rustore.ru/)
2. Создайте приложение
3. Получите:
   - `console_application_id` — идентификатор приложения
   - `API Key` — ключ для серверных запросов
   - `Secret Key` — секретный ключ для подписей

### Настройка товаров

1. В консоли RuStore перейдите в раздел «Монетизация»
2. Создайте товары:
   - **Потребляемые** (consumable) — можно купить многократно
   - **Непотребляемые** (non-consumable) — покупка один раз
   - **Подписки** (subscription) — регулярные платежи

---

## Серверная часть

### Шаг 1: Установка файлов

```bash
# Копируем gateway
cp app/payment_gateways/rustore.py /path/to/fastpay_connect/app/payment_gateways/

# Копируем тесты
cp tests/test_rustore.py /path/to/fastpay_connect/tests/
```

### Шаг 2: Настройка переменных окружения

Добавьте в `.env` файл:

```env
# RuStore Pay SDK
RUSTORE_CONSOLE_APPLICATION_ID=123456
RUSTORE_API_KEY=your_api_key_here
RUSTORE_SECRET_KEY=your_secret_key_here
RUSTORE_RETURN_URL=https://your-domain.com/payment/return
```

### Шаг 3: Обновление settings.py

Добавьте в `app/settings.py` после настроек Robokassa:

```python
# RuStore Pay SDK
rustore_console_application_id: Optional[str] = None
rustore_api_key: Optional[str] = None
rustore_secret_key: Optional[str] = None
rustore_return_url: str = "https://localhost:8080/payment/return"
rustore_ips: List[str] = Field(
    default_factory=lambda: [
        "185.165.128.0/24",
        "185.165.129.0/24",
        "185.165.130.0/24",
    ]
)
```

### Шаг 4: Создание API endpoints

Создайте файл `app/api/v1/routes/rustore.py`:

```python
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.payment_gateways.rustore import gateway

router = APIRouter(prefix="/rustore", tags=["RuStore"])


class ValidatePurchaseRequest(BaseModel):
    invoice_id: str
    expected_amount: Optional[float] = None
    product_id: Optional[str] = None


class ValidateSubscriptionRequest(BaseModel):
    purchase_id: str


class ConfirmPurchaseRequest(BaseModel):
    invoice_id: str


@router.post("/validate")
async def validate_purchase(request: ValidatePurchaseRequest):
    """Валидация покупки после оплаты в приложении."""
    try:
        result = await gateway.validate_purchase(
            invoice_id=request.invoice_id,
            expected_amount=request.expected_amount
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/validate-subscription")
async def validate_subscription(request: ValidateSubscriptionRequest):
    """Валидация активной подписки."""
    try:
        result = await gateway.validate_subscription(request.purchase_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/confirm")
async def confirm_purchase(request: ConfirmPurchaseRequest):
    """Подтверждение двухстадийной покупки."""
    try:
        result = await gateway.confirm_purchase(request.invoice_id)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cancel")
async def cancel_purchase(request: ConfirmPurchaseRequest):
    """Отмена двухстадийной покупки."""
    try:
        result = await gateway.cancel_purchase(request.invoice_id)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/purchases/{user_id}")
async def get_user_purchases(user_id: str):
    """Получение списка покупок пользователя."""
    return await gateway.get_user_purchases(user_id)


@router.get("/subscriptions/{user_id}")
async def get_user_subscriptions(user_id: str):
    """Получение списка подписок пользователя."""
    return await gateway.get_user_subscriptions(user_id)
```

### Шаг 5: Регистрация маршрутов

В `app/api/v1/routes/__init__.py` добавьте:

```python
from .rustore import router as rustore_router

# В список маршрутов
include_router(rustore_router)
```

---

## Android часть

### Шаг 1: Добавление зависимостей

В `build.gradle` (Project level):

```gradle
repositories {
    google()
    mavenCentral()
    maven {
        url = uri("https://artifactory-external.vkpartner.ru/artifactory/maven/")
    }
}
```

В `build.gradle` (App level):

```gradle
dependencies {
    implementation(platform("ru.rustore.sdk:bom:2025.11.01"))
    implementation("ru.rustore.sdk:pay")
}
```

### Шаг 2: Настройка AndroidManifest.xml

```xml
<application ...>
    <!-- RuStore Console Application ID -->
    <meta-data
        android:name="console_app_id_value"
        android:value="YOUR_CONSOLE_APPLICATION_ID" />
    
    <!-- Deeplink схема -->
    <meta-data
        android:name="sdk_pay_scheme_value"
        android:value="yourapp" />
</application>
```

### Шаг 3: Код платежей

Скопируйте файлы из `examples/android/` в ваш Android проект:
- `RuStorePaymentManager.kt` — менеджер платежей
- `FastPayApiClient.kt` — API клиент для серверной валидации

---

## Webhook настройка

### Шаг 1: Регистрация URL

В RuStore Console настройте webhook URL:
```
https://your-domain.com/api/v1/webhooks/rustore
```

### Шаг 2: Создание обработчика

В `app/routes/webhook_routes.py`:

```python
from app.payment_gateways.rustore import gateway

@router.post("/webhooks/rustore")
async def handle_rustore_webhook(request: Request):
    signature = request.headers.get("X-Signature", "")
    payload = await request.json()
    
    result = await gateway.handle_webhook(payload, signature)
    
    if result["status"] == "failed":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return {"status": "ok", "result": result}
```

---

## Тестирование

### Unit тесты

```bash
pytest tests/test_rustore.py -v
```

### Проверочный список

- [ ] Получены учётные данные RuStore
- [ ] Настроены переменные окружения
- [ ] Скопирован `rustore.py` в payment_gateways
- [ ] Обновлён `settings.py`
- [ ] Созданы API endpoints
- [ ] Настроен webhook URL в RuStore Console
- [ ] Добавлены зависимости в Android проект
- [ ] Настроен AndroidManifest.xml
- [ ] Реализован код платежей в приложении
- [ ] Протестирована валидация покупок
