/**
 * Пример интеграции RuStore Pay SDK в Android приложении.
 * 
 * Этот файл демонстрирует полную интеграцию Pay SDK для работы с покупками.
 * Адаптируйте код под архитектуру вашего приложения.
 * 
 * Документация: https://www.rustore.ru/help/sdk/pay
 */

package com.example.app.payment

import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import ru.rustore.sdk.pay.RuStorePayClient
import ru.rustore.sdk.pay.exception.RustorePaymentException
import ru.rustore.sdk.pay.model.ProductId
import ru.rustore.sdk.pay.model.ProductPurchase
import ru.rustore.sdk.pay.model.ProductPurchaseParams
import ru.rustore.sdk.pay.model.PurchaseId
import ru.rustore.sdk.pay.model.SubscriptionPurchase
import ru.rustore.sdk.pay.model.purchase.PreferredPurchaseType
import ru.rustore.sdk.pay.model.purchase.ProductPurchaseResult
import ru.rustore.sdk.pay.model.purchase.PurchaseAvailabilityResult
import ru.rustore.sdk.pay.model.theme.SdkTheme
import ru.rustore.sdk.pay.model.user.UserAuthorizationStatus
import java.util.UUID

/**
 * Активность для управления платежами через RuStore Pay SDK.
 */
class RuStorePaymentManager(
    private val activity: AppCompatActivity
) {
    companion object {
        private const val TAG = "RuStorePayment"
        
        // Идентификаторы продуктов (настройте в RuStore Console)
        const val PRODUCT_PREMIUM = "premium_monthly"
        const val PRODUCT_COINS_100 = "coins_100"
        const val PRODUCT_SUBSCRIPTION = "subscription_pro"
    }

    private val json = Json { ignoreUnknownKeys = true }

    // Интеракторы Pay SDK
    private val productInteractor by lazy {
        RuStorePayClient.instance.getProductInteractor()
    }
    
    private val purchaseInteractor by lazy {
        RuStorePayClient.instance.getPurchaseInteractor()
    }
    
    private val userInteractor by lazy {
        RuStorePayClient.instance.getUserInteractor()
    }
    
    private val intentInteractor by lazy {
        RuStorePayClient.instance.getIntentInteractor()
    }

    /**
     * Инициализация Pay SDK.
     * Вызовите этот метод в Activity.onCreate()
     */
    fun initialize(savedInstanceState: Bundle?) {
        if (savedInstanceState == null) {
            intentInteractor.proceedIntent(
                activity.intent,
                sdkTheme = SdkTheme.LIGHT
            )
        }
    }

    /**
     * Обработка нового intent (deeplink).
     * Вызовите этот метод в Activity.onNewIntent()
     */
    fun handleNewIntent(intent: android.content.Intent?) {
        intentInteractor.proceedIntent(
            intent,
            sdkTheme = SdkTheme.LIGHT
        )
    }

    /**
     * Проверка доступности платежей.
     */
    fun checkPaymentAvailability(
        onAvailable: () -> Unit,
        onUnavailable: (String) -> Unit,
        onError: (Throwable) -> Unit
    ) {
        purchaseInteractor
            .getPurchaseAvailability()
            .addOnSuccessListener { result ->
                when (result) {
                    PurchaseAvailabilityResult.Available -> {
                        Log.d(TAG, "Payments are available")
                        onAvailable()
                    }
                    is PurchaseAvailabilityResult.Unavailable -> {
                        Log.w(TAG, "Payments unavailable: ${result.cause}")
                        onUnavailable(result.cause.toString())
                    }
                }
            }
            .addOnFailureListener { error ->
                Log.e(TAG, "Failed to check payment availability", error)
                onError(error)
            }
    }

    /**
     * Проверка статуса авторизации пользователя.
     */
    fun checkUserAuthorization(
        onAuthorized: () -> Unit,
        onUnauthorized: () -> Unit,
        onError: (Throwable) -> Unit
    ) {
        userInteractor
            .getUserAuthorizationStatus()
            .addOnSuccessListener { result ->
                when (result) {
                    UserAuthorizationStatus.AUTHORIZED -> {
                        Log.d(TAG, "User is authorized")
                        onAuthorized()
                    }
                    UserAuthorizationStatus.UNAUTHORIZED -> {
                        Log.d(TAG, "User is not authorized")
                        onUnauthorized()
                    }
                }
            }
            .addOnFailureListener { error ->
                Log.e(TAG, "Failed to check user authorization", error)
                onError(error)
            }
    }

    /**
     * Получение списка продуктов.
     */
    fun fetchProducts(
        productIds: List<String>,
        onSuccess: (List<ProductInfo>) -> Unit,
        onError: (Throwable) -> Unit
    ) {
        productInteractor
            .getProducts(
                productsId = productIds.map { ProductId(it) }
            )
            .addOnSuccessListener { products ->
                val productInfoList = products.map { product ->
                    ProductInfo(
                        productId = product.productId,
                        title = product.title,
                        description = product.description,
                        price = product.price,
                        amountLabel = product.amountLabel,
                        currency = product.currency,
                        imageUrl = product.imageUrl,
                        type = product.type.name,
                        subscriptionInfo = product.subscriptionInfo?.let { subInfo ->
                            SubscriptionInfo(
                                periods = subInfo.periods?.map { period ->
                                    when (period) {
                                        is ru.rustore.sdk.pay.model.subscription.TrialPeriod ->
                                            PeriodInfo("trial", period.duration, period.price.toString())
                                        is ru.rustore.sdk.pay.model.subscription.PromoPeriod ->
                                            PeriodInfo("promo", period.duration, period.price.toString())
                                        is ru.rustore.sdk.pay.model.subscription.MainPeriod ->
                                            PeriodInfo("main", period.duration, period.price.toString())
                                        is ru.rustore.sdk.pay.model.subscription.GracePeriod ->
                                            PeriodInfo("grace", period.duration, null)
                                        is ru.rustore.sdk.pay.model.subscription.HoldPeriod ->
                                            PeriodInfo("hold", period.duration, null)
                                        else -> PeriodInfo("unknown", "", null)
                                    }
                                } ?: emptyList()
                            )
                        }
                    )
                }
                Log.d(TAG, "Fetched ${productInfoList.size} products")
                onSuccess(productInfoList)
            }
            .addOnFailureListener { error ->
                Log.e(TAG, "Failed to fetch products", error)
                onError(error)
            }
    }

    /**
     * Покупка продукта (одностадийная оплата).
     */
    fun purchaseProduct(
        productId: String,
        quantity: Int = 1,
        orderId: String = UUID.randomUUID().toString(),
        userId: String,
        userEmail: String? = null,
        developerPayload: Map<String, Any>? = null,
        onSuccess: (String) -> Unit,  // invoiceId
        onCancelled: () -> Unit,
        onError: (Throwable) -> Unit
    ) {
        val params = ProductPurchaseParams(
            productId = productId,
            quantity = quantity,
            orderId = orderId,
            appUserId = userId,
            appUserEmail = userEmail,
            developerPayload = developerPayload?.let { json.encodeToString(it) }
        )

        purchaseInteractor
            .purchase(
                params = params,
                preferredPurchaseType = PreferredPurchaseType.ONE_STEP,
                sdkTheme = SdkTheme.LIGHT
            )
            .addOnSuccessListener { result ->
                when (result) {
                    is ProductPurchaseResult.Success -> {
                        Log.d(TAG, "Purchase successful: ${result.invoiceId}")
                        onSuccess(result.invoiceId)
                    }
                    is ProductPurchaseResult.Cancelled -> {
                        Log.d(TAG, "Purchase cancelled by user")
                        onCancelled()
                    }
                    is ProductPurchaseResult.Failure -> {
                        Log.e(TAG, "Purchase failed: ${result.error}")
                        onError(Exception(result.error))
                    }
                }
            }
            .addOnFailureListener { error ->
                when (error) {
                    is RustorePaymentException.ProductPurchaseCancelled -> {
                        Log.d(TAG, "Purchase cancelled (exception)")
                        // Рекомендуется проверить статус покупки
                        onCancelled()
                    }
                    is RustorePaymentException.ProductPurchaseException -> {
                        Log.e(TAG, "Purchase exception: ${error.message}")
                        onError(error)
                    }
                    else -> {
                        Log.e(TAG, "Unknown purchase error", error)
                        onError(error)
                    }
                }
            }
    }

    /**
     * Покупка продукта (двухстадийная оплата с холдированием).
     */
    fun purchaseProductTwoStep(
        productId: String,
        quantity: Int = 1,
        orderId: String = UUID.randomUUID().toString(),
        userId: String,
        onSuccess: (String) -> Unit,  // invoiceId
        onError: (Throwable) -> Unit
    ) {
        val params = ProductPurchaseParams(
            productId = productId,
            quantity = quantity,
            orderId = orderId,
            appUserId = userId
        )

        purchaseInteractor
            .purchaseTwoStep(
                params = params,
                sdkTheme = SdkTheme.LIGHT
            )
            .addOnSuccessListener { result ->
                when (result) {
                    is ProductPurchaseResult.Success -> {
                        Log.d(TAG, "Two-step purchase successful: ${result.invoiceId}")
                        onSuccess(result.invoiceId)
                    }
                    else -> {
                        onError(Exception("Unexpected result: $result"))
                    }
                }
            }
            .addOnFailureListener { error ->
                Log.e(TAG, "Two-step purchase failed", error)
                onError(error)
            }
    }

    /**
     * Подтверждение двухстадийной покупки.
     */
    fun confirmTwoStepPurchase(
        purchaseId: String,
        onSuccess: () -> Unit,
        onError: (Throwable) -> Unit
    ) {
        purchaseInteractor
            .confirmTwoStepPurchase(PurchaseId(purchaseId))
            .addOnSuccessListener {
                Log.d(TAG, "Two-step purchase confirmed: $purchaseId")
                onSuccess()
            }
            .addOnFailureListener { error ->
                Log.e(TAG, "Failed to confirm two-step purchase", error)
                onError(error)
            }
    }

    /**
     * Отмена двухстадийной покупки.
     */
    fun cancelTwoStepPurchase(
        purchaseId: String,
        onSuccess: () -> Unit,
        onError: (Throwable) -> Unit
    ) {
        purchaseInteractor
            .cancelTwoStepPurchase(PurchaseId(purchaseId))
            .addOnSuccessListener {
                Log.d(TAG, "Two-step purchase cancelled: $purchaseId")
                onSuccess()
            }
            .addOnFailureListener { error ->
                Log.e(TAG, "Failed to cancel two-step purchase", error)
                onError(error)
            }
    }

    /**
     * Получение списка покупок пользователя.
     */
    fun fetchPurchases(
        onSuccess: (List<PurchaseInfo>) -> Unit,
        onError: (Throwable) -> Unit
    ) {
        purchaseInteractor
            .getPurchases()
            .addOnSuccessListener { purchases ->
                val purchaseInfoList = purchases.map { purchase ->
                    when (purchase) {
                        is ProductPurchase -> PurchaseInfo(
                            purchaseId = purchase.purchaseId,
                            productId = purchase.productId,
                            invoiceId = purchase.invoiceId,
                            status = purchase.status.name,
                            type = "product",
                            amount = purchase.price,
                            currency = purchase.currency,
                            purchaseTime = purchase.purchaseTime,
                            developerPayload = purchase.developerPayload
                        )
                        is SubscriptionPurchase -> PurchaseInfo(
                            purchaseId = purchase.purchaseId,
                            productId = purchase.productId,
                            invoiceId = purchase.invoiceId,
                            status = purchase.status.name,
                            type = "subscription",
                            amount = purchase.price,
                            currency = purchase.currency,
                            purchaseTime = purchase.purchaseTime,
                            expirationDate = purchase.expirationDate,
                            gracePeriodEnabled = purchase.gracePeriodEnabled
                        )
                    }
                }
                Log.d(TAG, "Fetched ${purchaseInfoList.size} purchases")
                onSuccess(purchaseInfoList)
            }
            .addOnFailureListener { error ->
                Log.e(TAG, "Failed to fetch purchases", error)
                onError(error)
            }
    }

    /**
     * Получение информации о конкретной покупке.
     */
    fun fetchPurchaseInfo(
        purchaseId: String,
        onSuccess: (PurchaseInfo) -> Unit,
        onError: (Throwable) -> Unit
    ) {
        purchaseInteractor
            .getPurchase(PurchaseId(purchaseId))
            .addOnSuccessListener { purchase ->
                val info = when (purchase) {
                    is ProductPurchase -> PurchaseInfo(
                        purchaseId = purchase.purchaseId,
                        productId = purchase.productId,
                        invoiceId = purchase.invoiceId,
                        status = purchase.status.name,
                        type = "product",
                        amount = purchase.price,
                        currency = purchase.currency,
                        purchaseTime = purchase.purchaseTime
                    )
                    is SubscriptionPurchase -> PurchaseInfo(
                        purchaseId = purchase.purchaseId,
                        productId = purchase.productId,
                        invoiceId = purchase.invoiceId,
                        status = purchase.status.name,
                        type = "subscription",
                        amount = purchase.price,
                        currency = purchase.currency,
                        purchaseTime = purchase.purchaseTime,
                        expirationDate = purchase.expirationDate
                    )
                }
                onSuccess(info)
            }
            .addOnFailureListener { error ->
                Log.e(TAG, "Failed to fetch purchase info", error)
                onError(error)
            }
    }
}

// Data classes для UI

@Serializable
data class ProductInfo(
    val productId: String,
    val title: String,
    val description: String?,
    val price: Int,
    val amountLabel: String,
    val currency: String,
    val imageUrl: String?,
    val type: String,
    val subscriptionInfo: SubscriptionInfo? = null
)

@Serializable
data class SubscriptionInfo(
    val periods: List<PeriodInfo>
)

@Serializable
data class PeriodInfo(
    val type: String,
    val duration: String,
    val price: String?
)

@Serializable
data class PurchaseInfo(
    val purchaseId: String,
    val productId: String,
    val invoiceId: String,
    val status: String,
    val type: String,
    val amount: Int,
    val currency: String,
    val purchaseTime: Long,
    val developerPayload: String? = null,
    val expirationDate: Long? = null,
    val gracePeriodEnabled: Boolean? = null
)
