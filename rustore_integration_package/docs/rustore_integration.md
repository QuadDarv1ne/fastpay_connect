# Интеграция RuStore Pay SDK

## Обзор

RuStore Pay SDK — это SDK для приёма платежей в мобильных приложениях от RuStore. Данная документация описывает интеграцию как серверной части (FastPay Connect), так и клиентской части (Android).

### Возможности

- **Разовые покупки** (consumable и non-consumable товары)
- **Подписки** с автоматическим продлением
- **Двухстадийная оплата** (холдирование средств)
- **Оплата купонами** и бонусами
- **Серверная валидация** покупок
- **Webhook уведомления** о смене статуса

### Поддерживаемые способы оплаты

- Банковские карты
- СБП (Система быстрых платежей)
- SberPay
- VK ID Pay (в разработке)

---

## Серверная интеграция

### 1. Конфигурация

Добавьте в файл `.env`:

```env
# RuStore Pay SDK
RUSTORE_CONSOLE_APPLICATION_ID=your_console_application_id
RUSTORE_API_KEY=your_api_key
RUSTORE_SECRET_KEY=your_secret_key
RUSTORE_RETURN_URL=https://your-domain.com/payment/return
```

#### Получение учётных данных

1. Зарегистрируйтесь в [Консоли разработчика RuStore](https://console.rustore.ru/)
2. Создайте приложение и получите `console_application_id`
3. В настройках приложения найдите `API Key` и `Secret Key`

### 2. Валидация покупок

После успешной оплаты на стороне клиента, рекомендуется валидировать покупку на сервере:

```python
from app.payment_gateways.rustore import gateway

async def validate_payment(invoice_id: str, expected_amount: float):
    """Валидация покупки после оплаты в приложении."""
    try:
        result = await gateway.validate_purchase(
            invoice_id=invoice_id,
            expected_amount=expected_amount
        )
        
        if result["valid"]:
            # Покупка валидна, предоставляем доступ
            grant_access(
                user_id=result["developer_payload"]["user_id"],
                product_id=result["product_id"]
            )
            return {"success": True, "data": result}
        else:
            return {"success": False, "error": "Invalid purchase"}
            
    except Exception as e:
        logger.error(f"Purchase validation failed: {e}")
        return {"success": False, "error": str(e)}
```

### 3. Валидация подписок

```python
from app.payment_gateways.rustore import gateway

async def validate_subscription(purchase_id: str):
    """Валидация активной подписки."""
    result = await gateway.validate_subscription(purchase_id)
    
    if result["valid"]:
        # Подписка активна
        expiration_date = result["expiration_date"]
        return {
            "active": True,
            "expires_at": expiration_date
        }
    else:
        # Подписка неактивна
        return {
            "active": False,
            "reason": result.get("reason")
        }
```

### 4. Обработка Webhook

#### Регистрация webhook endpoint

В RuStore Console настройте URL для webhook уведомлений:
```
https://your-domain.com/api/v1/webhooks/rustore
```

#### Обработка webhook

```python
from fastapi import APIRouter, Request, HTTPException
from app.payment_gateways.rustore import gateway

router = APIRouter()

@router.post("/webhooks/rustore")
async def handle_rustore_webhook(request: Request):
    """Обработка webhook уведомлений от RuStore."""
    # Получаем подпись из заголовка
    signature = request.headers.get("X-Signature", "")
    
    # Получаем тело запроса
    payload = await request.json()
    
    # Обрабатываем webhook
    result = await gateway.handle_webhook(payload, signature)
    
    if result["status"] == "failed":
        raise HTTPException(status_code=400, detail=result["message"])
    
    # Выполняем действие в зависимости от типа события
    action = result.get("action")
    order_id = result.get("order_id")
    
    if action == "fulfill_order":
        # Предоставляем доступ к контенту
        await fulfill_order(order_id)
    elif action == "cancel_order":
        # Отменяем заказ
        await cancel_order(order_id)
    elif action == "process_refund":
        # Обрабатываем возврат
        await process_refund(order_id)
    
    return {"status": "ok", "result": result}
```

### 5. Типы webhook событий

| Событие | Описание |
|---------|----------|
| `ORDER_PAID` | Заказ оплачен |
| `ORDER_CONFIRMED` | Заказ подтверждён |
| `ORDER_CANCELLED` | Заказ отменён |
| `ORDER_REFUNDED` | Возврат средств |
| `SUBSCRIPTION_CREATED` | Подписка создана |
| `SUBSCRIPTION_RENEWED` | Подписка продлена |
| `SUBSCRIPTION_CANCELLED` | Подписка отменена |
| `SUBSCRIPTION_EXPIRED` | Срок подписки истёк |

---

## Android интеграция

### 1. Добавление зависимостей

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

### 2. Настройка AndroidManifest.xml

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.app">

    <application
        android:name=".App"
        ...>

        <!-- RuStore Console Application ID -->
        <meta-data
            android:name="console_app_id_value"
            android:value="YOUR_CONSOLE_APPLICATION_ID" />

        <!-- Deeplink схема для возврата из RuStore -->
        <meta-data
            android:name="sdk_pay_scheme_value"
            android:value="yourscheme" />

        <!-- Activity для обработки deeplink -->
        <activity
            android:name=".PaymentActivity"
            android:exported="true"
            android:launchMode="singleTask">
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="yourscheme" />
            </intent-filter>
        </activity>

    </application>
</manifest>
```

### 3. Инициализация и обработка deeplink

```kotlin
// PaymentActivity.kt
class PaymentActivity : AppCompatActivity() {

    private val intentInteractor: IntentInteractor by lazy {
        RuStorePayClient.instance.getIntentInteractor()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_payment)

        if (savedInstanceState == null) {
            intentInteractor.proceedIntent(
                intent,
                sdkTheme = SdkTheme.LIGHT // или SdkTheme.DARK
            )
        }
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        intentInteractor.proceedIntent(
            intent,
            sdkTheme = SdkTheme.LIGHT
        )
    }
}
```

### 4. Проверка доступности платежей

```kotlin
RuStorePayClient.instance
    .getPurchaseInteractor()
    .getPurchaseAvailability()
    .addOnSuccessListener { result ->
        when (result) {
            PurchaseAvailabilityResult.Available -> {
                // Платежи доступны
                showPaymentUI()
            }
            is PurchaseAvailabilityResult.Unavailable -> {
                // Платежи недоступны
                showError(result.cause)
            }
        }
    }
    .addOnFailureListener { error ->
        // Ошибка проверки
        showError(error)
    }
```

### 5. Получение списка продуктов

```kotlin
RuStorePayClient.instance
    .getProductInteractor()
    .getProducts(
        productsId = listOf(
            ProductId("product_1"),
            ProductId("product_2"),
            ProductId("subscription_1")
        )
    )
    .addOnSuccessListener { products ->
        products.forEach { product ->
            Log.d("Product", "${product.title}: ${product.amountLabel}")
            
            // Проверяем информацию о подписке
            product.subscriptionInfo?.periods?.forEach { period ->
                when (period) {
                    is TrialPeriod -> {
                        Log.d("Subscription", "Trial: ${period.duration}")
                    }
                    is MainPeriod -> {
                        Log.d("Subscription", "Main: ${period.duration}, price: ${period.price}")
                    }
                    // ...
                }
            }
        }
    }
```

### 6. Покупка продукта

#### Одностадийная оплата

```kotlin
val params = ProductPurchaseParams(
    productId = "product_id",
    quantity = 1,
    orderId = UUID.randomUUID().toString(),
    developerPayload = json.encodeToString(
        mapOf("user_id" to currentUserId)
    ),
    appUserId = currentUserId,
    appUserEmail = userEmail
)

RuStorePayClient.instance
    .getPurchaseInteractor()
    .purchase(
        params = params,
        preferredPurchaseType = PreferredPurchaseType.ONE_STEP,
        sdkTheme = SdkTheme.LIGHT
    )
    .addOnSuccessListener { result ->
        when (result) {
            is ProductPurchaseResult.Success -> {
                // Покупка успешна, отправляем на сервер для валидации
                validateOnServer(result.invoiceId)
            }
            is ProductPurchaseResult.Cancelled -> {
                // Пользователь отменил покупку
                showCancelledMessage()
            }
            is ProductPurchaseResult.Failure -> {
                // Ошибка покупки
                showError(result.error)
            }
        }
    }
    .addOnFailureListener { error ->
        when (error) {
            is RustorePaymentException.ProductPurchaseCancelled -> {
                // Пользователь закрыл шторку
                checkPurchaseStatus()
            }
            is RustorePaymentException.ProductPurchaseException -> {
                // Ошибка покупки
                showError(error.message)
            }
        }
    }
```

#### Двухстадийная оплата

```kotlin
RuStorePayClient.instance
    .getPurchaseInteractor()
    .purchaseTwoStep(
        params = params,
        sdkTheme = SdkTheme.LIGHT
    )
    .addOnSuccessListener { result ->
        // Средства захолдированы, требуется подтверждение на сервере
        confirmPurchaseOnServer(result.invoiceId)
    }
```

### 7. Получение списка покупок

```kotlin
RuStorePayClient.instance
    .getPurchaseInteractor()
    .getPurchases()
    .addOnSuccessListener { purchases ->
        purchases.forEach { purchase ->
            when (purchase) {
                is ProductPurchase -> {
                    // Разовая покупка
                    handleProductPurchase(purchase)
                }
                is SubscriptionPurchase -> {
                    // Подписка
                    handleSubscription(purchase)
                }
            }
        }
    }
```

### 8. Подтверждение двухстадийной покупки

```kotlin
// На сервере после проверки
RuStorePayClient.instance
    .getPurchaseInteractor()
    .confirmTwoStepPurchase(
        purchaseId = PurchaseId("purchase_id")
    )
    .addOnSuccessListener {
        // Покупка подтверждена
    }
```

### 9. Отмена двухстадийной покупки

```kotlin
RuStorePayClient.instance
    .getPurchaseInteractor()
    .cancelTwoStepPurchase(
        purchaseId = PurchaseId("purchase_id")
    )
    .addOnSuccessListener {
        // Покупка отменена
    }
```

---

## Серверная валидация из Android

После успешной оплаты отправьте данные на сервер для валидации:

```kotlin
// ApiClient.kt
suspend fun validatePurchase(invoiceId: String): ValidationResult {
    return apiService.validatePurchase(
        ValidatePurchaseRequest(
            invoice_id = invoiceId,
            platform = "android",
            source = "rustore"
        )
    )
}

// PaymentViewModel.kt
fun onPurchaseSuccess(invoiceId: String) {
    viewModelScope.launch {
        try {
            val result = apiClient.validatePurchase(invoiceId)
            if (result.valid) {
                _purchaseState.value = PurchaseState.Completed(result)
            } else {
                _purchaseState.value = PurchaseState.Error("Validation failed")
            }
        } catch (e: Exception) {
            _purchaseState.value = PurchaseState.Error(e.message ?: "Unknown error")
        }
    }
}
```

---

## Статусы покупок

### Разовые покупки (ProductPurchase)

| Статус | Описание |
|--------|----------|
| `INVOICE_CREATED` | Счёт создан |
| `CANCELLED` | Покупка отменена |
| `PROCESSING` | Обработка платежа |
| `REJECTED` | Покупка отклонена |
| `CONFIRMED` | Покупка подтверждена |
| `PAID` | Покупка оплачена |
| `REFUNDING` | Возврат в процессе |
| `REFUNDED` | Возврат выполнен |

### Подписки (SubscriptionPurchase)

| Статус | Описание |
|--------|----------|
| `ACTIVE` | Подписка активна |
| `PAUSED` | Подписка приостановлена |
| `CANCELLED` | Подписка отменена |
| `EXPIRED` | Срок подписки истёк |
| `TERMINATED` | Подписка终止ирована |
| `CLOSED` | Подписка закрыта |

---

## Обработка ошибок

### Типы ошибок SDK

```kotlin
when (error) {
    is RustorePaymentException.ProductPurchaseCancelled -> {
        // Пользователь закрыл платёжную шторку
        // Рекомендуется проверить статус покупки
        checkPurchaseStatus()
    }
    is RustorePaymentException.ProductPurchaseException -> {
        // Общая ошибка покупки
        showError(error.message)
    }
    is RuStorePayInvalidActivePurchase -> {
        // Попытка покупки продукта неизвестного типа
        showError("Invalid product type")
    }
}
```

### Рекомендации по обработке

1. **Всегда проверяйте статус покупки** при получении ошибки отмены
2. **Используйте серверную валидацию** для критичных покупок
3. **Логируйте ошибки** для анализа проблем
4. **Предоставляйте понятные сообщения** пользователю

---

## Тестирование

### Sandbox режим

Для тестовых платежей используйте sandbox параметр:

```kotlin
// При создании продукта в консоли RuStore укажите тестовый режим
// Тестовые покупки не списывают реальные средства
```

### Тестовые карты

При тестировании используйте тестовые номера карт из документации RuStore.

---

## Миграция с billingClient SDK

Если вы переходите с устаревшего billingClient SDK:

### Изменение зависимостей

```gradle
// Старое (billingClient)
implementation("ru.rustore.sdk:billingclient")

// Новое (Pay SDK)
implementation("ru.rustore.sdk:pay")
```

### Изменение инициализации

```kotlin
// Старое (в коде)
val billingClient = RuStoreBillingClientFactory.create(
    context = this,
    consoleApplicationId = "your_id",
    deeplinkScheme = "yourscheme"
)

// Новое (в AndroidManifest.xml)
// См. раздел "Настройка AndroidManifest.xml"
```

### Особенности миграции подписок

- Разовые товары автоматически доступны в Pay SDK
- **Подписки не переносятся автоматически**
- На время миграции используйте оба SDK параллельно

---

## Полезные ссылки

- [Официальная документация RuStore Pay SDK](https://www.rustore.ru/help/sdk/pay)
- [Миграция с billingClient SDK](https://www.rustore.ru/help/sdk/pay/migration)
- [RuStore API Reference](https://www.rustore.ru/help/api/)
- [Консоль разработчика RuStore](https://console.rustore.ru/)
- [Telegram канал RuStore Dev](https://t.me/rustoredev)

---

## Поддержка

При возникновении вопросов обращайтесь:
- Email: support@rustore.ru (тема письма: "Pay SDK")
- GitHub Issues: [fastpay_connect/issues](https://github.com/QuadDarv1ne/fastpay_connect/issues)
