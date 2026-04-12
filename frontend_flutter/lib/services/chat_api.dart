import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

class ChatApiService {
  ChatApiService({
    String? baseUrl,
  }) : _baseUrl = baseUrl ?? _defaultBaseUrl();

  final String _baseUrl;

  String get baseUrl => _baseUrl;

  static String _defaultBaseUrl() {
    const defined = String.fromEnvironment('NOVA_API_URL', defaultValue: '');
    if (defined.isNotEmpty) return defined;

    if (kIsWeb) {
      final host = Uri.base.host;
      final scheme = Uri.base.scheme == 'https' ? 'https' : 'http';
      final isLocal = host == 'localhost' ||
          host == '127.0.0.1' ||
          host.startsWith('192.168.') ||
          host.startsWith('10.') ||
          host.startsWith('172.');

      if (host == 'api.andradeegomes.com') {
        return 'https://api.andradeegomes.com';
      }

      if (host == 'andradeegomes.com' || host.endsWith('.andradeegomes.com')) {
        return 'https://api.andradeegomes.com';
      }

      if (isLocal) {
        return '$scheme://$host:8000';
      }

      return '$scheme://$host';
    }

    return 'http://10.0.2.2:8000';
  }

  Uri _uri(String path) => Uri.parse('$_baseUrl$path');

  Future<Map<String, dynamic>> _requestJson(
    String method,
    String path, {
    Map<String, dynamic>? body,
  }) async {
    final uri = _uri(path);
    late http.Response response;

    final encoded = body == null ? null : jsonEncode(body);
    final headers = {'Content-Type': 'application/json'};

    switch (method) {
      case 'GET':
        response = await http.get(uri, headers: headers);
        break;
      case 'POST':
        response = await http.post(uri, headers: headers, body: encoded);
        break;
      case 'PUT':
        response = await http.put(uri, headers: headers, body: encoded);
        break;
      case 'DELETE':
        response = await http.delete(uri, headers: headers);
        break;
      default:
        throw Exception('Metodo HTTP nao suportado: $method');
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('Falha HTTP ${response.statusCode}');
    }

    final payload = jsonDecode(response.body);
    if (payload is! Map<String, dynamic>) {
      throw Exception('Resposta invalida do servidor.');
    }

    if (payload['ok'] != true) {
      throw Exception(payload['error']?.toString() ?? 'erro_desconhecido');
    }

    return payload;
  }

  Future<String> sendMessage(String message) async {
    final payload =
        await _requestJson('POST', '/chat', body: {'message': message});
    return payload['reply']?.toString() ?? 'Sem resposta.';
  }

  Future<bool> healthCheck() async {
    final payload = await _requestJson('GET', '/health');
    return payload['ok'] == true;
  }

  Future<Map<String, dynamic>> getSecurityAudit() async {
    final payload = await _requestJson('GET', '/security/audit');
    final audit = payload['audit'];
    if (audit is Map<String, dynamic>) return audit;
    if (audit is Map) return Map<String, dynamic>.from(audit);
    return {};
  }

  Future<List<Map<String, dynamic>>> getSecurityAuditHistory({
    int limit = 30,
  }) async {
    final lim = limit.clamp(1, 200);
    final payload =
        await _requestJson('GET', '/security/audit/history?limit=$lim');
    final items = payload['items'];
    if (items is! List) return [];
    return items
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  Future<Map<String, dynamic>> getAdminState() {
    return _requestJson('GET', '/admin/state');
  }

  Future<List<Map<String, dynamic>>> getKnowledge() async {
    final payload = await _requestJson('GET', '/knowledge');
    final items = payload['items'];
    if (items is! List) return [];
    return items
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  Future<List<Map<String, dynamic>>> createKnowledge({
    required String gatilho,
    required String resposta,
    required String categoria,
  }) async {
    final payload = await _requestJson(
      'POST',
      '/knowledge',
      body: {
        'gatilho': gatilho,
        'resposta': resposta,
        'categoria': categoria,
      },
    );
    final items = payload['items'];
    if (items is! List) return [];
    return items
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  Future<Map<String, dynamic>> updateKnowledge(
    String id, {
    String? gatilho,
    String? resposta,
    String? categoria,
    bool? ativo,
  }) async {
    final body = <String, dynamic>{};
    if (gatilho != null) body['gatilho'] = gatilho;
    if (resposta != null) body['resposta'] = resposta;
    if (categoria != null) body['categoria'] = categoria;
    if (ativo != null) body['ativo'] = ativo;
    final payload = await _requestJson('PUT', '/knowledge/$id', body: body);
    final item = payload['item'];
    if (item is! Map) return {};
    return Map<String, dynamic>.from(item);
  }

  Future<List<Map<String, dynamic>>> deleteKnowledge(String id) async {
    final payload = await _requestJson('DELETE', '/knowledge/$id');
    final items = payload['items'];
    if (items is! List) return [];
    return items
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  Future<List<Map<String, dynamic>>> getUsers() async {
    final payload = await _requestJson('GET', '/admin/users');
    final users = payload['users'];
    if (users is! List) return [];
    return users
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  Future<List<Map<String, dynamic>>> addUser(String name) async {
    final payload = await _requestJson(
      'POST',
      '/admin/users',
      body: {'nome': name, 'papel': 'usuario'},
    );
    final users = payload['users'];
    if (users is! List) return [];
    return users
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  Future<List<Map<String, dynamic>>> updateUser(
    String id, {
    String? name,
    bool? active,
  }) async {
    final body = <String, dynamic>{};
    if (name != null) body['nome'] = name;
    if (active != null) body['ativo'] = active;
    final payload = await _requestJson('PUT', '/admin/users/$id', body: body);
    final users = payload['users'];
    if (users is! List) return [];
    return users
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  Future<List<Map<String, dynamic>>> deleteUser(String id) async {
    final payload = await _requestJson('DELETE', '/admin/users/$id');
    final users = payload['users'];
    if (users is! List) return [];
    return users
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  Future<Map<String, dynamic>> getConfig() async {
    final payload = await _requestJson('GET', '/admin/config');
    final config = payload['config'];
    if (config is! Map) return {};
    return Map<String, dynamic>.from(config);
  }

  Future<Map<String, dynamic>> updateConfig(Map<String, dynamic> config) async {
    final payload = await _requestJson('POST', '/admin/config', body: config);
    final cfg = payload['config'];
    if (cfg is! Map) return {};
    return Map<String, dynamic>.from(cfg);
  }

  Future<String> sendTelegram(String message) async {
    final payload = await _requestJson('POST', '/telegram/send',
        body: {'message': message});
    return payload['message']?.toString() ?? 'Mensagem enviada.';
  }

  Future<Map<String, dynamic>> getMarketQuotes() async {
    final payload = await _requestJson('GET', '/market/quotes');
    final quotes = payload['quotes'];
    if (quotes is! Map) return {};
    return Map<String, dynamic>.from(quotes);
  }

  Future<String> getWeatherNow({String city = ''}) async {
    final suffix = city.trim().isEmpty
        ? '/weather/now'
        : '/weather/now?city=${Uri.encodeComponent(city.trim())}';
    final payload = await _requestJson('GET', suffix);
    return payload['summary']?.toString() ?? 'Sem clima no momento.';
  }

  Future<List<Map<String, dynamic>>> getReminders() async {
    final payload = await _requestJson('GET', '/reminders');
    final items = payload['items'];
    if (items is! List) return [];
    return items
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  Future<Map<String, dynamic>> addReminder({
    required String text,
    String when = '',
  }) async {
    return _requestJson(
      'POST',
      '/reminders',
      body: {'text': text, 'when': when},
    );
  }

  Future<Map<String, dynamic>> exportBackup() async {
    final payload = await _requestJson('GET', '/backup/export');
    final backup = payload['backup'];
    if (backup is Map<String, dynamic>) return backup;
    if (backup is Map) return Map<String, dynamic>.from(backup);
    return {};
  }

  Future<void> restoreBackup(Map<String, dynamic> backup) async {
    await _requestJson('POST', '/backup/restore', body: {'backup': backup});
  }

  Future<Map<String, dynamic>> synthesizeNeuralVoice(
    String text, {
    String voiceProfile = 'feminina',
  }) {
    return _requestJson(
      'POST',
      '/voice/neural',
      body: {
        'text': text,
        'voice_profile': voiceProfile,
      },
    );
  }
}
