import 'dart:io';

import 'package:flutter/services.dart';

class BackgroundWakeService {
  static const MethodChannel _channel = MethodChannel('nova/background_voice');

  static Future<void> start({
    String wakeWord = 'nova',
    bool allowVoiceOnLock = true,
  }) async {
    if (!Platform.isAndroid) return;
    await _channel.invokeMethod('startBackgroundWake', {
      'wakeWord': wakeWord,
      'allowVoiceOnLock': allowVoiceOnLock,
    });
  }

  static Future<void> stop() async {
    if (!Platform.isAndroid) return;
    await _channel.invokeMethod('stopBackgroundWake');
  }
}
