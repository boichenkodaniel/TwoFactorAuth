package com.example.twofa_app

import android.content.Context

class AppPreferences(context: Context) {
    private val sharedPreferences =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    var backendUrl: String
        get() = sharedPreferences.getString(KEY_BACKEND_URL, DEFAULT_BACKEND_URL).orEmpty()
        set(value) = sharedPreferences.edit().putString(KEY_BACKEND_URL, value.trim()).apply()

    var email: String
        get() = sharedPreferences.getString(KEY_EMAIL, "").orEmpty()
        set(value) = sharedPreferences.edit().putString(KEY_EMAIL, value.trim()).apply()

    var password: String
        get() = sharedPreferences.getString(KEY_PASSWORD, "").orEmpty()
        set(value) = sharedPreferences.edit().putString(KEY_PASSWORD, value).apply()

    var userId: String
        get() = sharedPreferences.getString(KEY_USER_ID, "").orEmpty()
        set(value) = sharedPreferences.edit().putString(KEY_USER_ID, value.trim()).apply()

    var fcmToken: String
        get() = sharedPreferences.getString(KEY_FCM_TOKEN, "").orEmpty()
        set(value) = sharedPreferences.edit().putString(KEY_FCM_TOKEN, value).apply()

    var currentRequestId: String
        get() = sharedPreferences.getString(KEY_REQUEST_ID, "").orEmpty()
        set(value) = sharedPreferences.edit().putString(KEY_REQUEST_ID, value).apply()

    var currentRequestStatus: String
        get() = sharedPreferences.getString(KEY_REQUEST_STATUS, REQUEST_STATUS_IDLE).orEmpty()
        set(value) = sharedPreferences.edit().putString(KEY_REQUEST_STATUS, value).apply()

    var currentSiteName: String
        get() = sharedPreferences.getString(KEY_SITE_NAME, "").orEmpty()
        set(value) = sharedPreferences.edit().putString(KEY_SITE_NAME, value).apply()

    fun saveIncomingRequest(requestId: String, siteName: String = "") {
        currentRequestId = requestId
        currentSiteName = siteName
        currentRequestStatus = REQUEST_STATUS_PENDING
    }

    fun clearCurrentRequest() {
        currentRequestId = ""
        currentSiteName = ""
        currentRequestStatus = REQUEST_STATUS_IDLE
    }

    companion object {
        private const val PREFS_NAME = "twofa_prefs"
        private const val KEY_BACKEND_URL = "backend_url"
        private const val KEY_EMAIL = "email"
        private const val KEY_PASSWORD = "password"
        private const val KEY_USER_ID = "user_id"
        private const val KEY_FCM_TOKEN = "fcm_token"
        private const val KEY_REQUEST_ID = "request_id"
        private const val KEY_REQUEST_STATUS = "request_status"
        private const val KEY_SITE_NAME = "site_name"

        const val DEFAULT_BACKEND_URL = "http://10.0.2.2:8000"
        const val REQUEST_STATUS_IDLE = "idle"
        const val REQUEST_STATUS_PENDING = "pending"
    }
}
