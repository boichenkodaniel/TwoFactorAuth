package com.example.twofa_app

import android.content.Intent
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class FCMService : FirebaseMessagingService() {
    private val serviceScope = CoroutineScope(Dispatchers.IO)

    override fun onNewToken(token: String) {
        super.onNewToken(token)

        val preferences = AppPreferences(applicationContext)
        preferences.fcmToken = token

        val backendUrl = preferences.backendUrl
        val email = preferences.email
        val password = preferences.password
        if (backendUrl.isBlank() || email.isBlank() || password.isBlank()) {
            return
        }

        serviceScope.launch {
            ApiClient.registerDevice(backendUrl, email, password, token)
        }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)

        val requestId = message.data["request_id"] ?: return
        val siteName = message.data["site_name"].orEmpty()
        val type = message.data["type"]
        if (type != "login_request") {
            return
        }

        val preferences = AppPreferences(applicationContext)
        preferences.saveIncomingRequest(requestId, siteName)

        NotificationHelper.showLoginRequestNotification(applicationContext, requestId, siteName)
        sendBroadcast(
            Intent(ACTION_LOGIN_REQUEST)
                .setPackage(packageName)
                .putExtra(NotificationHelper.EXTRA_REQUEST_ID, requestId)
                .putExtra(NotificationHelper.EXTRA_SITE_NAME, siteName),
        )
    }

    companion object {
        const val ACTION_LOGIN_REQUEST = "com.example.twofa_app.LOGIN_REQUEST"
    }
}
