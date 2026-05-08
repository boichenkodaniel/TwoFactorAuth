package com.example.twofa_app

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.view.isVisible
import androidx.lifecycle.lifecycleScope
import com.example.twofa_app.databinding.ActivityMainBinding
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    private lateinit var preferences: AppPreferences

    private val pushReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            val requestId = intent?.getStringExtra(NotificationHelper.EXTRA_REQUEST_ID) ?: return
            val siteName = intent.getStringExtra(NotificationHelper.EXTRA_SITE_NAME).orEmpty()
            preferences.saveIncomingRequest(requestId, siteName)
            renderState(message = "New login request received.")
        }
    }

    private val notificationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (!granted) {
                showToast("Notification permission was denied. Push messages may be hidden.")
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        preferences = AppPreferences(this)
        NotificationHelper.ensureChannel(this)

        setupUi()
        loadStoredValues()
        handleIntent(intent)
        requestNotificationPermissionIfNeeded()
        fetchCurrentToken()
        syncPendingRequest()
    }

    override fun onStart() {
        super.onStart()
        ContextCompat.registerReceiver(
            this,
            pushReceiver,
            IntentFilter(FCMService.ACTION_LOGIN_REQUEST),
            ContextCompat.RECEIVER_NOT_EXPORTED,
        )
    }

    override fun onStop() {
        unregisterReceiver(pushReceiver)
        super.onStop()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleIntent(intent)
    }

    private fun setupUi() {
        binding.registerDeviceButton.setOnClickListener {
            persistInputs()
            registerCurrentDevice()
        }

        binding.unregisterDeviceButton.setOnClickListener {
            persistInputs()
            unregisterCurrentDevice()
        }

        binding.approveButton.setOnClickListener {
            submitDecision(approved = true)
        }

        binding.denyButton.setOnClickListener {
            submitDecision(approved = false)
        }
    }

    private fun loadStoredValues() {
        binding.backendUrlInput.setText(preferences.backendUrl)
        binding.emailInput.setText(preferences.email)
        binding.passwordInput.setText(preferences.password)
        renderState()
    }

    private fun persistInputs() {
        preferences.backendUrl = binding.backendUrlInput.text?.toString().orEmpty()
        preferences.email = binding.emailInput.text?.toString().orEmpty()
        preferences.password = binding.passwordInput.text?.toString().orEmpty()
    }

    private fun fetchCurrentToken() {
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (!task.isSuccessful) {
                renderState(message = "Failed to fetch FCM token: ${task.exception?.message.orEmpty()}")
                return@addOnCompleteListener
            }

            val token = task.result.orEmpty()
            if (token.isBlank()) {
                return@addOnCompleteListener
            }

            preferences.fcmToken = token
            renderState()
        }
    }

    private fun registerCurrentDevice() {
        val backendUrl = binding.backendUrlInput.text?.toString().orEmpty().trim()
        val email = binding.emailInput.text?.toString().orEmpty().trim()
        val password = binding.passwordInput.text?.toString().orEmpty()
        val token = preferences.fcmToken

        if (backendUrl.isBlank() || email.isBlank() || password.isBlank()) {
            showToast("Enter backend URL, email, and password first.")
            return
        }

        if (token.isBlank()) {
            showToast("FCM token is not ready yet.")
            fetchCurrentToken()
            return
        }

        lifecycleScope.launch {
            setLoading(true)
            val result = ApiClient.registerDevice(backendUrl, email, password, token)
            setLoading(false)

            result.onSuccess { registration ->
                preferences.userId = registration.userId
                renderState(message = registration.message)
                syncPendingRequest()
            }.onFailure { error ->
                renderState(message = "Registration failed: ${error.message}")
            }
        }
    }

    private fun unregisterCurrentDevice() {
        val backendUrl = binding.backendUrlInput.text?.toString().orEmpty().trim()
        val userId = preferences.userId

        if (backendUrl.isBlank()) {
            showToast("Enter backend URL first.")
            return
        }

        if (userId.isBlank()) {
            showToast("Device is not registered yet.")
            return
        }

        lifecycleScope.launch {
            setLoading(true)
            val result = ApiClient.unregisterDevice(backendUrl, userId)
            setLoading(false)

            result.onSuccess { message ->
                preferences.userId = ""
                preferences.clearCurrentRequest()
                renderState(message = message)
            }.onFailure { error ->
                renderState(message = "Unregister failed: ${error.message}")
            }
        }
    }

    private fun submitDecision(approved: Boolean) {
        persistInputs()

        val backendUrl = preferences.backendUrl
        val requestId = preferences.currentRequestId
        if (backendUrl.isBlank() || requestId.isBlank()) {
            showToast("No active login request.")
            return
        }

        lifecycleScope.launch {
            setLoading(true)
            val result = ApiClient.sendDecision(backendUrl, requestId, approved)
            setLoading(false)

            result.onSuccess { message ->
                preferences.currentRequestStatus = if (approved) "approved" else "denied"
                renderState(message = message)
                syncPendingRequest()
            }.onFailure { error ->
                renderState(message = "Request failed: ${error.message}")
            }
        }
    }

    private fun syncPendingRequest() {
        val backendUrl = preferences.backendUrl
        val userId = preferences.userId
        if (backendUrl.isBlank() || userId.isBlank()) {
            return
        }

        lifecycleScope.launch {
            val result = ApiClient.getPendingRequest(backendUrl, userId)
            result.onSuccess { pending ->
                preferences.currentRequestId = pending.requestId
                preferences.currentRequestStatus = pending.status
                preferences.currentSiteName = pending.siteName
                renderState()
            }.onFailure {
                preferences.clearCurrentRequest()
                renderState()
            }
        }
    }

    private fun renderState(message: String? = null) {
        binding.registeredUserValue.text = preferences.userId.ifBlank { "Not linked yet" }
        binding.tokenValue.text = preferences.fcmToken.ifBlank { "Token not received yet" }
        binding.requestIdValue.text = preferences.currentRequestId.ifBlank { "No active request" }
        binding.requestStatusValue.text = preferences.currentRequestStatus
        binding.requestSiteValue.text = preferences.currentSiteName.ifBlank { "Unknown site" }
        binding.messageText.text = message ?: "Waiting for push notifications."

        val hasPendingRequest =
            preferences.currentRequestId.isNotBlank() &&
                preferences.currentRequestStatus == AppPreferences.REQUEST_STATUS_PENDING

        binding.requestCard.isVisible = preferences.currentRequestId.isNotBlank()
        binding.approveButton.isEnabled = hasPendingRequest
        binding.denyButton.isEnabled = hasPendingRequest
        binding.unregisterDeviceButton.isEnabled = preferences.userId.isNotBlank()
    }

    private fun handleIntent(intent: Intent?) {
        val requestId = intent?.getStringExtra(NotificationHelper.EXTRA_REQUEST_ID) ?: return
        val siteName = intent.getStringExtra(NotificationHelper.EXTRA_SITE_NAME).orEmpty()
        preferences.saveIncomingRequest(requestId, siteName)
        renderState(message = "Login request opened from notification.")
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            return
        }

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) ==
            PackageManager.PERMISSION_GRANTED
        ) {
            return
        }

        notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
    }

    private fun setLoading(loading: Boolean) {
        binding.progressBar.isVisible = loading
        binding.registerDeviceButton.isEnabled = !loading
        binding.unregisterDeviceButton.isEnabled = !loading && preferences.userId.isNotBlank()
        binding.approveButton.isEnabled =
            !loading &&
                preferences.currentRequestId.isNotBlank() &&
                preferences.currentRequestStatus == AppPreferences.REQUEST_STATUS_PENDING
        binding.denyButton.isEnabled = binding.approveButton.isEnabled
    }

    private fun showToast(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    }
}
