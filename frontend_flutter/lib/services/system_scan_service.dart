import 'package:battery_plus/battery_plus.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:package_info_plus/package_info_plus.dart';

import 'chat_api.dart';
import 'platform_capabilities.dart';

class SystemScanService {
  final DeviceInfoPlugin _deviceInfo = DeviceInfoPlugin();
  final Battery _battery = Battery();

  Future<String> buildDetailedReport({
    required ChatApiService api,
    required Map<String, dynamic> config,
    required bool hasAdminPin,
    required bool canUseBiometric,
  }) async {
    final backendOnline = await _backendOnline(api);
    final appInfo = await _appInfo();
    final deviceInfo = await _deviceInfoHuman();
    final batteryInfo = await _batteryHuman();

    final adminGuard = config['admin_guard'] == true;
    final allowVoiceOnLock = config['allow_voice_on_lock'] != false;
    final wakeWord =
        (config['wake_word']?.toString().trim().isNotEmpty ?? false)
            ? config['wake_word'].toString().trim()
            : 'nova';

    final linhas = <String>[
      'Varredura detalhada (software + hardware):',
      '- Plataforma: ${PlatformCapabilities.platformName}',
      '- Backend API: ${backendOnline ? 'online' : 'offline'}',
      '- App: $appInfo',
      '- Dispositivo: $deviceInfo',
      '- Bateria: $batteryInfo',
      '- Wake word: "$wakeWord"',
      '- Monitor em segundo plano: ${PlatformCapabilities.supportsBackgroundWake ? 'suportado' : 'limitado'}',
      '- Comando por voz com tela bloqueada: ${allowVoiceOnLock ? 'ativado' : 'desativado'}',
      '- Proteção admin: ${adminGuard ? 'ativada' : 'desativada'}',
      '- PIN admin configurado: ${hasAdminPin ? 'sim' : 'não'}',
      '- Biometria no dispositivo: ${canUseBiometric ? 'disponível' : 'indisponível'}',
      '- Compatibilidade geral:',
      PlatformCapabilities.matrixHuman(),
    ];

    return linhas.join('\n');
  }

  Future<bool> _backendOnline(ChatApiService api) async {
    try {
      return await api.healthCheck();
    } catch (_) {
      return false;
    }
  }

  Future<String> _appInfo() async {
    try {
      final p = await PackageInfo.fromPlatform();
      return '${p.appName} v${p.version} (${p.buildNumber})';
    } catch (_) {
      return 'não disponível';
    }
  }

  Future<String> _batteryHuman() async {
    try {
      final lvl = await _battery.batteryLevel;
      final state = await _battery.batteryState;
      final estado = switch (state) {
        BatteryState.charging => 'carregando',
        BatteryState.discharging => 'descarregando',
        BatteryState.connectedNotCharging => 'conectada sem carregar',
        BatteryState.full => 'cheia',
        BatteryState.unknown => 'desconhecido',
      };
      return '$lvl% ($estado)';
    } catch (_) {
      return 'não disponível';
    }
  }

  Future<String> _deviceInfoHuman() async {
    try {
      if (PlatformCapabilities.isWeb) {
        final w = await _deviceInfo.webBrowserInfo;
        final browser = w.browserName.name;
        final platform = (w.platform ?? 'web').trim();
        final vendor = (w.vendor ?? '').trim();
        final base = '$browser · ${platform.isEmpty ? 'web' : platform}';
        return vendor.isEmpty ? base : '$base · $vendor';
      }

      if (PlatformCapabilities.isAndroid) {
        final a = await _deviceInfo.androidInfo;
        final fabricante = a.manufacturer;
        final modelo = a.model;
        final versao = a.version.release;
        final sdk = a.version.sdkInt;
        final patch = a.version.securityPatch;
        final fisico = a.isPhysicalDevice ? 'físico' : 'emulador';
        return '$fabricante $modelo · Android $versao (SDK $sdk) · patch $patch · $fisico';
      }

      if (PlatformCapabilities.isIOS) {
        final i = await _deviceInfo.iosInfo;
        final nome = i.name;
        final modelo = i.model;
        final versao = i.systemVersion;
        final fisico = i.isPhysicalDevice ? 'físico' : 'simulador';
        return '$nome $modelo · iOS $versao · $fisico';
      }

      if (PlatformCapabilities.isWindows) {
        final w = await _deviceInfo.windowsInfo;
        return '${w.computerName} · Windows ${w.displayVersion}';
      }

      if (PlatformCapabilities.isLinux) {
        final l = await _deviceInfo.linuxInfo;
        return '${l.name} ${l.version ?? ''}'.trim();
      }

      if (PlatformCapabilities.isMacOS) {
        final m = await _deviceInfo.macOsInfo;
        return '${m.model} · macOS ${m.osRelease}';
      }
    } catch (_) {
      return 'não disponível';
    }

    return 'não disponível';
  }
}
