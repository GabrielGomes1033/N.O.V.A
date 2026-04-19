package com.nova.app.frontend_flutter

import android.Manifest
import android.content.ContentUris
import android.content.ContentValues
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.provider.CalendarContract
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterFragmentActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.util.TimeZone

class MainActivity : FlutterFragmentActivity() {
    private val backgroundVoiceChannelName = "nova/background_voice"
    private val deviceCalendarChannelName = "nova/device_calendar"
    private val calendarPermissionRequestCode = 4021
    private var pendingCalendarResult: MethodChannel.Result? = null
    private var pendingCalendarCall: MethodCall? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, backgroundVoiceChannelName)
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

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, deviceCalendarChannelName)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "createEvent" -> handleCreateCalendarEvent(call, result)
                    else -> result.notImplemented()
                }
            }
    }

    private fun hasCalendarPermissions(): Boolean {
        val readGranted = ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.READ_CALENDAR,
        ) == PackageManager.PERMISSION_GRANTED
        val writeGranted = ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.WRITE_CALENDAR,
        ) == PackageManager.PERMISSION_GRANTED
        return readGranted && writeGranted
    }

    private fun handleCreateCalendarEvent(call: MethodCall, result: MethodChannel.Result) {
        if (hasCalendarPermissions()) {
            createCalendarEvent(call, result)
            return
        }

        if (pendingCalendarResult != null) {
            result.error(
                "calendar_request_busy",
                "Ja existe uma solicitacao de permissao de calendario em andamento.",
                null,
            )
            return
        }

        pendingCalendarCall = call
        pendingCalendarResult = result
        ActivityCompat.requestPermissions(
            this,
            arrayOf(
                Manifest.permission.READ_CALENDAR,
                Manifest.permission.WRITE_CALENDAR,
            ),
            calendarPermissionRequestCode,
        )
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray,
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != calendarPermissionRequestCode) return

        val result = pendingCalendarResult
        val call = pendingCalendarCall
        pendingCalendarResult = null
        pendingCalendarCall = null

        if (result == null || call == null) return

        val granted = grantResults.isNotEmpty() && grantResults.all {
            it == PackageManager.PERMISSION_GRANTED
        }
        if (!granted) {
            result.error(
                "calendar_permission_denied",
                "Permissao de calendario negada no Android.",
                null,
            )
            return
        }

        createCalendarEvent(call, result)
    }

    private fun createCalendarEvent(call: MethodCall, result: MethodChannel.Result) {
        val title = call.argument<String>("title")?.trim().orEmpty()
        val description = call.argument<String>("description")?.trim().orEmpty()
        val location = call.argument<String>("location")?.trim().orEmpty()
        val preferredEmail = call.argument<String>("preferredEmail")?.trim().orEmpty()
        val timezone = call.argument<String>("timezone")?.trim()
            ?.takeIf { it.isNotEmpty() }
            ?: TimeZone.getDefault().id
        val startMillis = longArg(call, "startMillis")
        val endMillis = longArg(call, "endMillis")

        if (title.isBlank()) {
            result.error("calendar_title_required", "Titulo do evento obrigatorio.", null)
            return
        }
        if (startMillis <= 0L || endMillis <= 0L || endMillis <= startMillis) {
            result.error("calendar_time_invalid", "Data ou horario invalidos.", null)
            return
        }

        val selectedCalendar = resolveCalendar(preferredEmail)
        if (selectedCalendar == null) {
            result.error(
                "calendar_not_found",
                "Nenhuma agenda disponivel foi encontrada no dispositivo.",
                null,
            )
            return
        }

        val values = ContentValues().apply {
            put(CalendarContract.Events.CALENDAR_ID, selectedCalendar.id)
            put(CalendarContract.Events.TITLE, title)
            put(CalendarContract.Events.DESCRIPTION, description)
            put(CalendarContract.Events.EVENT_LOCATION, location)
            put(CalendarContract.Events.DTSTART, startMillis)
            put(CalendarContract.Events.DTEND, endMillis)
            put(CalendarContract.Events.EVENT_TIMEZONE, timezone)
            put(CalendarContract.Events.HAS_ALARM, 0)
        }

        try {
            val insertedUri = contentResolver.insert(CalendarContract.Events.CONTENT_URI, values)
            if (insertedUri == null) {
                result.error(
                    "calendar_insert_failed",
                    "Nao consegui gravar o evento no calendario do Android.",
                    null,
                )
                return
            }

            val eventId = ContentUris.parseId(insertedUri)
            result.success(
                mapOf(
                    "ok" to true,
                    "provider" to "device_calendar",
                    "event_id" to eventId.toString(),
                    "calendar_id" to selectedCalendar.id.toString(),
                    "calendar_name" to selectedCalendar.displayName,
                    "calendar_owner" to selectedCalendar.owner,
                    "title" to title,
                    "start_at" to startMillis,
                    "end_at" to endMillis,
                    "timezone" to timezone,
                ),
            )
        } catch (error: Exception) {
            result.error(
                "calendar_insert_failed",
                "Falha ao criar evento no calendario: ${error.message}",
                null,
            )
        }
    }

    private fun longArg(call: MethodCall, key: String): Long {
        return when (val value = call.argument<Any>(key)) {
            is Int -> value.toLong()
            is Long -> value
            is Double -> value.toLong()
            is Float -> value.toLong()
            is String -> value.toLongOrNull() ?: 0L
            else -> 0L
        }
    }

    private fun resolveCalendar(preferredEmail: String): CalendarSelection? {
        val projection = arrayOf(
            CalendarContract.Calendars._ID,
            CalendarContract.Calendars.CALENDAR_DISPLAY_NAME,
            CalendarContract.Calendars.OWNER_ACCOUNT,
            CalendarContract.Calendars.ACCOUNT_NAME,
            CalendarContract.Calendars.ACCOUNT_TYPE,
            CalendarContract.Calendars.IS_PRIMARY,
        )
        val selection =
            "${CalendarContract.Calendars.VISIBLE} = 1 AND ${CalendarContract.Calendars.SYNC_EVENTS} = 1"
        val candidates = mutableListOf<CalendarSelection>()

        contentResolver.query(
            CalendarContract.Calendars.CONTENT_URI,
            projection,
            selection,
            null,
            null,
        )?.use { cursor ->
            val idIndex = cursor.getColumnIndexOrThrow(CalendarContract.Calendars._ID)
            val displayNameIndex =
                cursor.getColumnIndexOrThrow(CalendarContract.Calendars.CALENDAR_DISPLAY_NAME)
            val ownerIndex = cursor.getColumnIndexOrThrow(CalendarContract.Calendars.OWNER_ACCOUNT)
            val accountNameIndex = cursor.getColumnIndexOrThrow(CalendarContract.Calendars.ACCOUNT_NAME)
            val accountTypeIndex = cursor.getColumnIndexOrThrow(CalendarContract.Calendars.ACCOUNT_TYPE)
            val primaryIndex = cursor.getColumnIndexOrThrow(CalendarContract.Calendars.IS_PRIMARY)

            while (cursor.moveToNext()) {
                candidates.add(
                    CalendarSelection(
                        id = cursor.getLong(idIndex),
                        displayName = cursor.getString(displayNameIndex).orEmpty(),
                        owner = cursor.getString(ownerIndex).orEmpty(),
                        accountName = cursor.getString(accountNameIndex).orEmpty(),
                        accountType = cursor.getString(accountTypeIndex).orEmpty(),
                        isPrimary = cursor.getInt(primaryIndex) == 1,
                    ),
                )
            }
        }

        if (candidates.isEmpty()) return null

        val normalizedEmail = preferredEmail.trim().lowercase()
        if (normalizedEmail.isNotEmpty()) {
            candidates.firstOrNull {
                it.owner.lowercase() == normalizedEmail || it.accountName.lowercase() == normalizedEmail
            }?.let { return it }
        }

        candidates.firstOrNull {
            it.isPrimary && it.accountType.contains("google", ignoreCase = true)
        }?.let { return it }

        candidates.firstOrNull {
            it.accountType.contains("google", ignoreCase = true)
        }?.let { return it }

        return candidates.firstOrNull()
    }

    private data class CalendarSelection(
        val id: Long,
        val displayName: String,
        val owner: String,
        val accountName: String,
        val accountType: String,
        val isPrimary: Boolean,
    )
}
