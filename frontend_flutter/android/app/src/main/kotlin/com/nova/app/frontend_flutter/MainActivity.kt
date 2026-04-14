package com.nova.app.frontend_flutter

import android.content.Intent
import android.os.Build
import io.flutter.embedding.android.FlutterFragmentActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterFragmentActivity() {
    private val channelName = "nova/background_voice"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "startBackgroundWake" -> {
                        val wakeWord = call.argument<String>("wakeWord") ?: "nova"
                        val allowVoiceOnLock = call.argument<Boolean>("allowVoiceOnLock") ?: true
                        val intent = Intent(this, NovaWakeService::class.java).apply {
                            putExtra("wakeWord", wakeWord)
                            putExtra("allowVoiceOnLock", allowVoiceOnLock)
                        }
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                            startForegroundService(intent)
                        } else {
                            startService(intent)
                        }
                        result.success(true)
                    }

                    "stopBackgroundWake" -> {
                        stopService(Intent(this, NovaWakeService::class.java))
                        result.success(true)
                    }

                    else -> result.notImplemented()
                }
            }
    }
}
