package com.example.twofa_app

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

object ApiClient {
    data class DeviceRegistrationResult(
        val userId: String,
        val message: String,
    )

    data class PendingRequestResult(
        val requestId: String,
        val status: String,
        val siteName: String,
    )

    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .build()

    suspend fun registerDevice(
        baseUrl: String,
        email: String,
        password: String,
        token: String,
    ): Result<DeviceRegistrationResult> = postJson(
        url = "${normalizeBaseUrl(baseUrl)}/device/register",
        payload = JSONObject()
            .put("email", email)
            .put("password", password)
            .put("fcm_token", token)
            .toString(),
    ) { body ->
        val json = JSONObject(body)
        DeviceRegistrationResult(
            userId = json.optString("user_id"),
            message = json.optString("message", "Device registered successfully"),
        )
    }

    suspend fun unregisterDevice(baseUrl: String, userId: String): Result<String> = postJson(
        url = "${normalizeBaseUrl(baseUrl)}/device/unregister",
        payload = JSONObject().put("user_id", userId).toString(),
    ) { body ->
        JSONObject(body).optString("message", "Device unregistered successfully")
    }

    suspend fun sendDecision(
        baseUrl: String,
        requestId: String,
        approved: Boolean,
    ): Result<String> {
        val endpoint = if (approved) "approve" else "deny"
        return postJson(
            url = "${normalizeBaseUrl(baseUrl)}/2fa/push/$endpoint",
            payload = JSONObject().put("request_id", requestId).toString(),
        ) { body ->
            JSONObject(body).optString("message", if (approved) "Login approved" else "Login denied")
        }
    }

    suspend fun getPendingRequest(baseUrl: String, userId: String): Result<PendingRequestResult> =
        getJson("${normalizeBaseUrl(baseUrl)}/2fa/push/pending/$userId") { body ->
            val json = JSONObject(body)
            PendingRequestResult(
                requestId = json.optString("request_id"),
                status = json.optString("status"),
                siteName = json.optString("site_name"),
            )
        }

    private suspend fun <T> postJson(
        url: String,
        payload: String,
        onSuccess: (String) -> T,
    ): Result<T> = withContext(Dispatchers.IO) {
        runCatching {
            val request = Request.Builder()
                .url(url)
                .post(payload.toRequestBody(jsonMediaType))
                .build()

            client.newCall(request).execute().use { response ->
                val responseBody = response.body?.string().orEmpty()
                if (!response.isSuccessful) {
                    val detail = responseBody.ifBlank { "HTTP ${response.code}" }
                    error(detail)
                }
                onSuccess(responseBody)
            }
        }
    }

    private suspend fun <T> getJson(
        url: String,
        onSuccess: (String) -> T,
    ): Result<T> = withContext(Dispatchers.IO) {
        runCatching {
            val request = Request.Builder()
                .url(url)
                .get()
                .build()

            client.newCall(request).execute().use { response ->
                val responseBody = response.body?.string().orEmpty()
                if (!response.isSuccessful) {
                    val detail = responseBody.ifBlank { "HTTP ${response.code}" }
                    error(detail)
                }
                onSuccess(responseBody)
            }
        }
    }

    private fun normalizeBaseUrl(baseUrl: String): String = baseUrl.trim().trimEnd('/')
}
