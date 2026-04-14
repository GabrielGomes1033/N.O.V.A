package com.nova.app.frontend_flutter

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.app.KeyguardManager
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import java.text.Normalizer
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class NovaWakeService : Service(), RecognitionListener {
    private var speechRecognizer: SpeechRecognizer? = null
    private var recognizerIntent: Intent? = null
    private var wakeWord: String = "nova"
    private var allowVoiceOnLock: Boolean = true
    private val handler = Handler(Looper.getMainLooper())
    private var tts: TextToSpeech? = null
    private var wakeLock: PowerManager.WakeLock? = null

    companion object {
        private const val CHANNEL_ID = "nova_wake_service"
        private const val NOTIFICATION_ID = 8842
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification("Escutando wake word em segundo plano"))
        acquireWakeLock()
        setupTts()
        setupSpeechRecognizer()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        wakeWord = intent?.getStringExtra("wakeWord")?.trim()?.lowercase(Locale.getDefault())?.ifEmpty { "nova" } ?: "nova"
        allowVoiceOnLock = intent?.getBooleanExtra("allowVoiceOnLock", true) ?: true
        startListening()
        return START_STICKY
    }

    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacksAndMessages(null)
        speechRecognizer?.cancel()
        speechRecognizer?.destroy()
        speechRecognizer = null
        tts?.stop()
        tts?.shutdown()
        tts = null
        releaseWakeLock()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun setupTts() {
        tts = TextToSpeech(this) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.language = Locale("pt", "BR")
                tts?.setPitch(1.03f)
                tts?.setSpeechRate(0.95f)
            }
        }
    }

    private fun acquireWakeLock() {
        try {
            val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
            wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "nova:background_wake").apply {
                setReferenceCounted(false)
                acquire()
            }
        } catch (_: Exception) {
        }
    }

    private fun releaseWakeLock() {
        try {
            wakeLock?.let {
                if (it.isHeld) {
                    it.release()
                }
            }
        } catch (_: Exception) {
        } finally {
            wakeLock = null
        }
    }

    private fun setupSpeechRecognizer() {
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            stopSelf()
            return
        }

        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this).apply {
            setRecognitionListener(this@NovaWakeService)
        }

        recognizerIntent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "pt-BR")
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
            putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, packageName)
        }
    }

    private fun startListening() {
        val granted = ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
        if (!granted) {
            stopSelf()
            return
        }

        try {
            speechRecognizer?.cancel()
            speechRecognizer?.startListening(recognizerIntent)
        } catch (_: Exception) {
            scheduleRestart()
        }
    }

    private fun scheduleRestart(delayMs: Long = 600L) {
        handler.postDelayed({ startListening() }, delayMs)
    }

    private fun buildNotification(content: String): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("NOVA em segundo plano")
            .setContentText(content)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setOngoing(true)
            .build()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val channel = NotificationChannel(
            CHANNEL_ID,
            "NOVA Wake Service",
            NotificationManager.IMPORTANCE_LOW
        )
        channel.description = "Escuta contínua da wake word da NOVA"
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(channel)
    }

    private fun normalize(text: String): String {
        val noAccents = Normalizer.normalize(text.lowercase(Locale.getDefault()), Normalizer.Form.NFD)
            .replace("\\p{Mn}+".toRegex(), "")
        return noAccents.replace("[^a-z0-9 ]".toRegex(), " ").replace("\\s+".toRegex(), " ").trim()
    }

    private fun containsWakeWord(text: String): Boolean {
        val t = normalize(text)
        val w = normalize(wakeWord)
        return t.split(" ").contains(w)
    }

    private fun commandAfterWake(text: String): String {
        val clean = normalize(text)
        val w = normalize(wakeWord)
        val idx = clean.indexOf(w)
        if (idx < 0) return ""
        val raw = clean.substring(idx + w.length).trim()
        return raw
    }

    private fun isDeviceLocked(): Boolean {
        val km = getSystemService(Context.KEYGUARD_SERVICE) as KeyguardManager
        return km.isKeyguardLocked
    }

    private fun speak(text: String) {
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "nova_bg_reply")
    }

    private fun handleBackgroundCommand(command: String) {
        if (!allowVoiceOnLock && isDeviceLocked()) {
            speak("Modo bloqueado ativo. Desbloqueie para comandos de voz.")
            return
        }

        val cmd = normalize(command)
        if (cmd.isBlank()) {
            speak("Oi chefe.")
            return
        }

        when {
            cmd.contains("que horas sao") || cmd.contains("qual a hora") -> {
                val hora = SimpleDateFormat("HH:mm", Locale("pt", "BR")).format(Date())
                speak("Agora são $hora.")
            }
            cmd.contains("que dia e hoje") || cmd.contains("qual a data") -> {
                val data = SimpleDateFormat("dd 'de' MMMM", Locale("pt", "BR")).format(Date())
                speak("Hoje é $data.")
            }
            cmd.contains("status") || cmd.contains("voce esta ai") || cmd.contains("você está ai") -> {
                speak("Estou ativa em segundo plano.")
            }
            cmd.contains("abrir nova") || cmd.contains("abrir aplicativo") -> {
                launchApp()
            }
            cmd.contains("parar monitor") || cmd.contains("parar escuta") -> {
                speak("Encerrando monitor de voz em segundo plano.")
                stopSelf()
            }
            else -> {
                speak("Comando recebido. Para ações completas, diga abrir NOVA.")
            }
        }
    }

    private fun launchApp() {
        val launch = packageManager.getLaunchIntentForPackage(packageName)
        if (launch != null) {
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            startActivity(launch)
        }
    }

    private fun onWakeDetected(command: String) {
        handleBackgroundCommand(command)

        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(NOTIFICATION_ID, buildNotification("Wake word detectada"))

        scheduleRestart(1200)
    }

    override fun onReadyForSpeech(params: android.os.Bundle?) {}

    override fun onBeginningOfSpeech() {}

    override fun onRmsChanged(rmsdB: Float) {}

    override fun onBufferReceived(buffer: ByteArray?) {}

    override fun onEndOfSpeech() {}

    override fun onError(error: Int) {
        scheduleRestart()
    }

    override fun onResults(results: android.os.Bundle?) {
        val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION) ?: arrayListOf()
        var detectedCommand = ""
        val found = matches.any {
            val txt = it ?: ""
            if (containsWakeWord(txt)) {
                detectedCommand = commandAfterWake(txt)
                true
            } else {
                false
            }
        }
        if (found) {
            onWakeDetected(detectedCommand)
        } else {
            scheduleRestart()
        }
    }

    override fun onPartialResults(partialResults: android.os.Bundle?) {
        val matches = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION) ?: arrayListOf()
        var detectedCommand = ""
        val found = matches.any {
            val txt = it ?: ""
            if (containsWakeWord(txt)) {
                detectedCommand = commandAfterWake(txt)
                true
            } else {
                false
            }
        }
        if (found) {
            onWakeDetected(detectedCommand)
        }
    }

    override fun onEvent(eventType: Int, params: android.os.Bundle?) {}
}
