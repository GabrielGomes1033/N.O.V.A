import 'package:flutter/services.dart';

import 'platform_capabilities.dart';

class BackgroundWakeService {
  static const MethodChannel _channel = MethodChannel('nova/background_voice');

  static Future<void> start({
    String wakeWord = 'nova',
    bool allowVoiceOnLock = true,
  }) async {
    if (!PlatformCapabilities.isAndroid) return;
    try {
      await _channel.invokeMethod('startBackgroundWake', {
        'wakeWord': wakeWord,
        'allowVoiceOnLock': allowVoiceOnLock,
      });
    } catch (_) {
      // Runner sem canal nativo não deve quebrar o app.
    }
  }

  static Future<void> stop() async {
    if (!PlatformCapabilities.isAndroid) return;
    try {
      await _channel.invokeMethod('stopBackgroundWake');
    } catch (_) {
      // Runner sem canal nativo não deve quebrar o app.
    }
  }
}
