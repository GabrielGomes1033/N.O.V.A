import 'dart:io';

import 'package:android_intent_plus/android_intent.dart';
import 'package:url_launcher/url_launcher.dart';

class DeviceConnectivityService {
  Future<bool> _launchAndroidIntent(AndroidIntent intent) async {
    if (!Platform.isAndroid) return false;
    try {
      await intent.launch();
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<bool> openBluetoothSettings() async {
    if (!Platform.isAndroid) return false;
    return _launchAndroidIntent(
      const AndroidIntent(action: 'android.settings.BLUETOOTH_SETTINGS'),
    );
  }

  Future<bool> openCastSettings() async {
    if (!Platform.isAndroid) return false;
    final castOk = await _launchAndroidIntent(
      const AndroidIntent(action: 'android.settings.CAST_SETTINGS'),
    );
    if (castOk) return true;
    return _launchAndroidIntent(
      const AndroidIntent(action: 'android.settings.WIRELESS_SETTINGS'),
    );
  }

  Future<bool> openAndroidAuto() async {
    if (!Platform.isAndroid) return false;
    final appOk = await _launchAndroidIntent(
      const AndroidIntent(
        action: 'android.intent.action.MAIN',
        category: 'android.intent.category.LAUNCHER',
        package: 'com.google.android.projection.gearhead',
      ),
    );
    if (appOk) return true;

    final marketUri = Uri.parse(
      'https://play.google.com/store/apps/details?id=com.google.android.projection.gearhead',
    );
    return launchUrl(marketUri, mode: LaunchMode.externalApplication);
  }

  Future<bool> openTermux() async {
    if (!Platform.isAndroid) return false;
    final appOk = await _launchAndroidIntent(
      const AndroidIntent(
        action: 'android.intent.action.MAIN',
        category: 'android.intent.category.LAUNCHER',
        package: 'com.termux',
      ),
    );
    if (appOk) return true;

    final marketUri = Uri.parse('https://play.google.com/store/apps/details?id=com.termux');
    return launchUrl(marketUri, mode: LaunchMode.externalApplication);
  }
}
