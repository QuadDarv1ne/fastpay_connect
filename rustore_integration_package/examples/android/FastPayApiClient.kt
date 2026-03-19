/**
 * API клиент для серверной валидации покупок RuStore.
 * 
 * Этот файл демонстрирует взаимодействие Android клиента
 * с серверной частью FastPay Connect.
 */

package com.example.app.payment

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

/**
 * Клиент для API FastPay Connect.
 */
class FastPayApiClient(
    private val baseUrl: String = "https://your-domain.com/api/v1"
) {
    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
    }
    
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    /**
     * Валидация покупки на сервере.
     * 
     * Вызывайте этот метод после успешной оплаты в RuStore SDK
     * для подтверждения подлинности транзакции.
     */
    suspend fun validatePurchase(
        invoiceId: String,
        expectedAmount: Int? = null,
        productId: String? = null
    ): ValidationResult = withContext(Dispatchers.IO) {
        val request = ValidatePurchaseRequest(
            invoice_id = invoiceId,
            expected_amount = expectedAmount,
            product_id = productId,
            platform = "android",
            source = "rustore"
        )
        
        val requestBody = json.encodeToString(
            ValidatePurchaseRequest.serializer(),
            request
        ).toRequestBody("application/json".toMediaType())
        
        val httpRequest = Request.Builder()
            .url("$baseUrl/rustore/validate")
            .post(requestBody)
            .header("Content-Type", "application/json")
            .build()
        
        val response = httpClient.newCall(httpRequest).execute()
        
        if (response.isSuccessful) {
            val responseBody = response.body?.string() ?: "{}"
            json.decodeFromString(ValidationResult.serializer(), responseBody)
        } else {
            ValidationResult(
                valid = false,
                error = "HTTP ${response.code}: ${response.message}"
            )
        }
    }

    /**
     * Валидация подписки.
     */
    suspend fun validateSubscription(
        purchaseId: String
    ): SubscriptionValidationResult = withContext(Dispatchers.IO) {
        val requestBody = json.encodeToString(
            ValidateSubscriptionRequest.serializer(),
            ValidateSubscriptionRequest(purchase_id = purchaseId)
        ).toRequestBody("application/json".toMediaType())
        
        val httpRequest = Request.Builder()
            .url("$baseUrl/rustore/validate-subscription")
            .post(requestBody)
            .header("Content-Type", "application/json")
            .build()
        
        val response = httpClient.newCall(httpRequest).execute()
        
        if (response.isSuccessful) {
            val responseBody = response.body?.string() ?: "{}"
            json.decodeFromString(SubscriptionValidationResult.serializer(), responseBody)
        } else {
            SubscriptionValidationResult(
                valid = false,
                error = "HTTP ${response.code}: ${response.message}"
            )
        }
    }

    /**
     * Подтверждение двухстадийной покупки.
     */
    suspend fun confirmTwoStepPurchase(
        invoiceId: String
    ): ConfirmResult = withContext(Dispatchers.IO) {
        val requestBody = json.encodeToString(
            ConfirmRequest.serializer(),
            ConfirmRequest(invoice_id = invoiceId)
        ).toRequestBody("application/json".toMediaType())
        
        val httpRequest = Request.Builder()
            .url("$baseUrl/rustore/confirm")
            .post(requestBody)
            .header("Content-Type", "application/json")
            .build()
        
        val response = httpClient.newCall(httpRequest).execute()
        
        if (response.isSuccessful) {
            val responseBody = response.body?.string() ?: "{}"
            json.decodeFromString(ConfirmResult.serializer(), responseBody)
        } else {
            ConfirmResult(
                success = false,
                error = "HTTP ${response.code}: ${response.message}"
            )
        }
    }

    /**
     * Отмена двухстадийной покупки.
     */
    suspend fun cancelTwoStepPurchase(
        invoiceId: String
    ): CancelResult = withContext(Dispatchers.IO) {
        val requestBody = json.encodeToString(
            CancelRequest.serializer(),
            CancelRequest(invoice_id = invoiceId)
        ).toRequestBody("application/json".toMediaType())
        
        val httpRequest = Request.Builder()
            .url("$baseUrl/rustore/cancel")
            .post(requestBody)
            .header("Content-Type", "application/json")
            .build()
        
        val response = httpClient.newCall(httpRequest).execute()
        
        if (response.isSuccessful) {
            val responseBody = response.body?.string() ?: "{}"
            json.decodeFromString(CancelResult.serializer(), responseBody)
        } else {
            CancelResult(
                success = false,
                error = "HTTP ${response.code}: ${response.message}"
            )
        }
    }
}

// Request/Response models

@Serializable
data class ValidatePurchaseRequest(
    val invoice_id: String,
    val expected_amount: Int? = null,
    val product_id: String? = null,
    val platform: String = "android",
    val source: String = "rustore"
)

@Serializable
data class ValidationResult(
    val valid: Boolean,
    val purchase_id: String? = null,
    val invoice_id: String? = null,
    val status: String? = null,
    val amount: Int? = null,
    val currency: String? = null,
    val product_id: String? = null,
    val purchase_time: Long? = null,
    val error: String? = null
)

@Serializable
data class ValidateSubscriptionRequest(
    val purchase_id: String
)

@Serializable
data class SubscriptionValidationResult(
    val valid: Boolean,
    val purchase_id: String? = null,
    val status: String? = null,
    val product_id: String? = null,
    val expiration_date: Long? = null,
    val start_time: Long? = null,
    val grace_period_enabled: Boolean? = null,
    val reason: String? = null,
    val error: String? = null
)

@Serializable
data class ConfirmRequest(
    val invoice_id: String
)

@Serializable
data class ConfirmResult(
    val success: Boolean,
    val invoice_id: String? = null,
    val status: String? = null,
    val error: String? = null
)

@Serializable
data class CancelRequest(
    val invoice_id: String
)

@Serializable
data class CancelResult(
    val success: Boolean,
    val invoice_id: String? = null,
    val status: String? = null,
    val error: String? = null
)
