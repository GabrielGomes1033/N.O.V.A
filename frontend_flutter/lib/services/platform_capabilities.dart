import 'dart:io';

class PlatformCapabilities {
  static bool get isAndroid => Platform.isAndroid;
  static bool get isIOS => Platform.isIOS;
  static bool get isDesktop =>
      Platform.isWindows || Platform.isLinux || Platform.isMacOS;

  static bool get supportsBackgroundWake => isAndroid;
  static bool get supportsWakeInForeground => true;
  static bool get supportsLocalMusicLibrary => true;
  static bool get supportsNotifications => isAndroid || isIOS;
  static bool get supportsDriveAndMarket => true;
  static bool get supportsBluetoothConnect => isAndroid || isIOS;
  static bool get supportsCastScreen => isAndroid;
  static bool get supportsAndroidAuto => isAndroid;
  static bool get supportsTermuxIntegration => isAndroid;

  static String get platformName {
    if (Platform.isAndroid) return 'Android';
    if (Platform.isIOS) return 'iOS';
    if (Platform.isWindows) return 'Windows';
    if (Platform.isLinux) return 'Linux';
    if (Platform.isMacOS) return 'macOS';
    return 'Desconhecido';
  }

  static Map<String, bool> matrix() {
    return {
      'wake_foreground': supportsWakeInForeground,
      'wake_background': supportsBackgroundWake,
      'music_library': supportsLocalMusicLibrary,
      'notifications': supportsNotifications,
      'drive_market_web': supportsDriveAndMarket,
      'bluetooth': supportsBluetoothConnect,
      'cast_screen': supportsCastScreen,
      'android_auto': supportsAndroidAuto,
      'termux': supportsTermuxIntegration,
    };
  }

  static String matrixHuman() {
    final m = matrix();
    String yn(bool v) => v ? 'Sim' : 'Parcial/Não';
    return 'Dispositivo atual: $platformName\n'
        'Wake word em primeiro plano: ${yn(m['wake_foreground'] == true)}\n'
        'Wake word em segundo plano: ${yn(m['wake_background'] == true)}\n'
        'Biblioteca de músicas local: ${yn(m['music_library'] == true)}\n'
        'Notificações de lembretes: ${yn(m['notifications'] == true)}\n'
        'Integrações web (Drive/mercado/pesquisa): ${yn(m['drive_market_web'] == true)}\n'
        'Bluetooth: ${yn(m['bluetooth'] == true)}\n'
        'Cast/Espelhar tela: ${yn(m['cast_screen'] == true)}\n'
        'Android Auto: ${yn(m['android_auto'] == true)}\n'
        'Termux (atalho): ${yn(m['termux'] == true)}';
  }

  static List<Map<String, String>> matrixRich() {
    return [
      {
        'key': 'wake_foreground',
        'label': 'Wake Word (1º plano)',
        'status': 'completo',
        'detail': 'Funciona com o app aberto em $platformName.',
      },
      {
        'key': 'wake_background',
        'label': 'Wake Word (2º plano)',
        'status': supportsBackgroundWake ? 'completo' : 'indisponivel',
        'detail': supportsBackgroundWake
            ? 'Serviço em background ativo no Android.'
            : 'Nesta plataforma ainda nao ha servico de wake em background.',
      },
      {
        'key': 'music_library',
        'label': 'Biblioteca de Música Local',
        'status': supportsLocalMusicLibrary ? 'completo' : 'indisponivel',
        'detail': supportsLocalMusicLibrary
            ? 'Seleção, busca e reprodução local de arquivos de áudio.'
            : 'Sem suporte local de música nesta plataforma.',
      },
      {
        'key': 'notifications',
        'label': 'Notificações de Lembretes',
        'status': supportsNotifications
            ? 'completo'
            : isDesktop
                ? 'parcial'
                : 'indisponivel',
        'detail': supportsNotifications
            ? 'Alertas locais com horário.'
            : isDesktop
                ? 'Dependente de suporte do SO/runner.'
                : 'Sem suporte nativo de notificação nesta plataforma.',
      },
      {
        'key': 'drive_market_web',
        'label': 'Pesquisa/Drive/Mercado',
        'status': 'completo',
        'detail': 'Depende de backend ativo e internet.',
      },
      {
        'key': 'bluetooth',
        'label': 'Bluetooth e Acessórios',
        'status': supportsBluetoothConnect ? 'completo' : 'indisponivel',
        'detail': supportsBluetoothConnect
            ? 'Atalho por comando de voz/texto para parear dispositivos.'
            : 'Sem suporte de atalho Bluetooth nesta plataforma.',
      },
      {
        'key': 'cast_screen',
        'label': 'TV/Telas (Cast)',
        'status': supportsCastScreen ? 'completo' : 'parcial',
        'detail': supportsCastScreen
            ? 'Abre configurações de transmissão/espelhamento.'
            : 'Pode depender de recursos nativos do sistema.',
      },
      {
        'key': 'android_auto',
        'label': 'Android Auto',
        'status': supportsAndroidAuto ? 'completo' : 'indisponivel',
        'detail': supportsAndroidAuto
            ? 'Abre Android Auto (ou Play Store caso não esteja instalado).'
            : 'Disponível apenas em Android.',
      },
      {
        'key': 'termux',
        'label': 'Termux (Modo Segurança)',
        'status': supportsTermuxIntegration ? 'completo' : 'indisponivel',
        'detail': supportsTermuxIntegration
            ? 'Atalho para Termux com foco em automação defensiva.'
            : 'Disponível apenas em Android.',
      },
    ];
  }
}
