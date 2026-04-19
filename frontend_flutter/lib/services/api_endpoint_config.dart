import 'package:flutter/foundation.dart';

import 'platform_capabilities.dart';

class ApiEndpointConfig {
  ApiEndpointConfig({
    required this.baseUrl,
    required this.source,
  });

  final String baseUrl;
  final String source;

  static List<ApiEndpointConfig> candidates({String? explicitBaseUrl}) {
    final out = <ApiEndpointConfig>[];

    void push(String raw, String source) {
      final normalized = normalizeBaseUrl(raw);
      if (normalized.isEmpty) return;
      if (out.any((item) => item.baseUrl == normalized)) return;
      out.add(ApiEndpointConfig(baseUrl: normalized, source: source));
    }

    final localOverride = normalizeBaseUrl(explicitBaseUrl ?? '');
    if (localOverride.isNotEmpty) {
      push(localOverride, 'configuracao_local');
      return out;
    }

    const defined = String.fromEnvironment('NOVA_API_URL', defaultValue: '');
    final envUrl = normalizeBaseUrl(defined);
    if (envUrl.isNotEmpty) {
      push(envUrl, 'dart_define');
      return out;
    }

    if (kIsWeb) {
      final host = Uri.base.host.trim();
      final scheme = Uri.base.scheme == 'https' ? 'https' : 'http';
      final isLocal = host == 'localhost' ||
          host == '127.0.0.1' ||
          host.startsWith('192.168.') ||
          host.startsWith('10.') ||
          host.startsWith('172.');

      if (host == 'api.andradeegomes.com') {
        push('https://api.andradeegomes.com', 'web_producao');
        return out;
      }

      if (host == 'andradeegomes.com' || host.endsWith('.andradeegomes.com')) {
        push('https://api.andradeegomes.com', 'web_subdominio');
        return out;
      }

      if (isLocal && host.isNotEmpty) {
        push('$scheme://$host:8000', 'web_mesmo_host');
        push(Uri.base.origin, 'web_mesma_origem');
        return out;
      }

      if (host.isNotEmpty) {
        push('$scheme://$host', 'web_host_atual');
        return out;
      }
    }

    if (PlatformCapabilities.isAndroid) {
      push('http://10.0.2.2:8000', 'android_emulador');
      push('http://127.0.0.1:8000', 'android_loopback');
      push('http://localhost:8000', 'android_localhost');
      return out;
    }

    push(
      'http://127.0.0.1:8000',
      PlatformCapabilities.isIOS ? 'ios_simulador_ou_local' : 'localhost',
    );
    push('http://localhost:8000', 'localhost_alias');
    return out;
  }

  static ApiEndpointConfig resolve({String? explicitBaseUrl}) {
    return candidates(explicitBaseUrl: explicitBaseUrl).first;
  }

  static String normalizeBaseUrl(String raw) {
    var value = raw.trim();
    if (value.isEmpty) return '';

    if (!value.contains('://')) {
      value = 'http://$value';
    }

    final uri = Uri.tryParse(value);
    if (uri == null || uri.host.trim().isEmpty) return '';

    final normalizedPath = uri.path == '/'
        ? ''
        : (uri.path.endsWith('/') && uri.path.length > 1
            ? uri.path.substring(0, uri.path.length - 1)
            : uri.path);
    final normalized = uri.replace(
      path: normalizedPath,
    );

    final asText = normalized.toString();
    return asText.endsWith('/')
        ? asText.substring(0, asText.length - 1)
        : asText;
  }
}
