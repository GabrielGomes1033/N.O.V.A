import 'dart:convert';

import 'package:http/http.dart' as http;

class ChatApiService {
  ChatApiService({
    String? baseUrl,
  }) : _baseUrl = baseUrl ??
            const String.fromEnvironment(
              'NOVA_API_URL',
              defaultValue: 'http://10.0.2.2:8000',
            );

  final String _baseUrl;

  String get baseUrl => _baseUrl;

  Future<String> sendMessage(String message) async {
    final uri = Uri.parse('$_baseUrl/chat');
    final response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'message': message}),
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('Falha HTTP ${response.statusCode}');
    }

    final payload = jsonDecode(response.body) as Map<String, dynamic>;
    final ok = payload['ok'] == true;
    if (!ok) {
      throw Exception(payload['error']?.toString() ?? 'erro_desconhecido');
    }

    return payload['reply']?.toString() ?? 'Sem resposta.';
  }

  Future<Map<String, dynamic>> exportBackup() async {
    final uri = Uri.parse('$_baseUrl/backup/export');
    final response = await http.get(uri);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('Falha HTTP ${response.statusCode}');
    }
    final payload = jsonDecode(response.body) as Map<String, dynamic>;
    if (payload['ok'] != true) {
      throw Exception(payload['error']?.toString() ?? 'erro_export_backup');
    }
    final backup = payload['backup'];
    if (backup is Map<String, dynamic>) return backup;
    return {};
  }

  Future<void> restoreBackup(Map<String, dynamic> backup) async {
    final uri = Uri.parse('$_baseUrl/backup/restore');
    final response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'backup': backup}),
    );
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('Falha HTTP ${response.statusCode}');
    }
    final payload = jsonDecode(response.body) as Map<String, dynamic>;
    if (payload['ok'] != true) {
      throw Exception(payload['error']?.toString() ?? 'erro_restore_backup');
    }
  }
}
