import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import 'api_endpoint_config.dart';

class ApiHttpException implements Exception {
  ApiHttpException({
    required this.method,
    required this.path,
    required this.statusCode,
    required this.url,
    required this.message,
    this.responseBody = '',
  });

  final String method;
  final String path;
  final int statusCode;
  final String url;
  final String message;
  final String responseBody;

  @override
  String toString() {
    return 'API $method $path falhou (HTTP $statusCode). $message';
  }
}

class ChatApiService {
  ChatApiService({
    String? baseUrl,
  }) : _endpoint = ApiEndpointConfig.resolve(explicitBaseUrl: baseUrl);

  static const Duration _requestTimeout = Duration(seconds: 18);

  ApiEndpointConfig _endpoint;

  String get baseUrl => _endpoint.baseUrl;
  String get baseUrlSource => _endpoint.source;

  void updateBaseUrl(String? baseUrl) {
    _endpoint = ApiEndpointConfig.resolve(explicitBaseUrl: baseUrl);
  }

  Uri _uriForBase(String baseUrl, String path) => Uri.parse('$baseUrl$path');

  Future<http.Response> _performHttp(
    String method,
    Uri uri, {
    required Map<String, String> headers,
    String? encodedBody,
  }) {
    switch (method) {
      case 'GET':
        return http.get(uri, headers: headers).timeout(_requestTimeout);
      case 'POST':
        return http
            .post(uri, headers: headers, body: encodedBody)
            .timeout(_requestTimeout);
      case 'PUT':
        return http
            .put(uri, headers: headers, body: encodedBody)
            .timeout(_requestTimeout);
      case 'DELETE':
        return http.delete(uri, headers: headers).timeout(_requestTimeout);
      default:
        throw Exception('Metodo HTTP nao suportado: $method');
    }
  }

  List<String> _fallbackPaths(String path) {
    final out = <String>[];

    if (!path.startsWith('/api/')) {
      out.add('/api$path');
    }
    if (path.startsWith('/api/')) {
      out.add(path.replaceFirst('/api', ''));
    }

    if (path == '/autonomy/status') {
      out.add('/autonomia/status');
    } else if (path == '/autonomy/config') {
      out.add('/autonomia/config');
    } else if (path == '/autonomy/task') {
      out.add('/autonomia/tarefa');
      out.add('/autonomia/task');
    } else if (path == '/documents/analyze') {
      out.add('/documentos/analisar');
      out.add('/document/analyze');
      out.add('/docs/analyze');
    } else if (path == '/jarvis/status') {
      out.add('/assistant/status');
    }

    final seen = <String>{path};
    final deduped = <String>[];
    for (final item in out) {
      if (item.trim().isEmpty) continue;
      if (seen.add(item)) deduped.add(item);
    }
    return deduped;
  }

  String _endpointHint({
    required String path,
    required int statusCode,
    required String body,
  }) {
    if (statusCode == 404 &&
        (path.startsWith('/autonomy') ||
            path.startsWith('/jarvis') ||
            path.startsWith('/actions') ||
            path.startsWith('/documents') ||
            path.startsWith('/agent') ||
            path.startsWith('/ops') ||
            path.startsWith('/help') ||
            path.startsWith('/memory/subjects') ||
            path.startsWith('/memory/recent') ||
            path.startsWith('/voice/status'))) {
      return 'Endpoint não encontrado nesse backend. '
          'A API está desatualizada para este recurso. '
          'Atualize/deploy o `backend_python/api_server.py` mais recente.';
    }
    if (statusCode == 401) {
      return 'Não autorizado. Verifique token/credenciais da API.';
    }
    if (statusCode == 403) {
      return 'Acesso negado (RBAC/permissão).';
    }
    if (body.trim().isNotEmpty) {
      return body.trim();
    }
    return 'Falha HTTP $statusCode';
  }

  Map<String, dynamic> _decodePayload(String body) {
    final decoded = jsonDecode(body);
    if (decoded is! Map<String, dynamic>) {
      throw Exception('Resposta invalida do servidor.');
    }
    return decoded;
  }

  Future<Map<String, dynamic>> _requestJson(
    String method,
    String path, {
    Map<String, dynamic>? body,
  }) async {
    return _requestJsonAtBase(
      _endpoint.baseUrl,
      method,
      path,
      body: body,
    );
  }

  Future<Map<String, dynamic>> _requestJsonAtBase(
    String baseUrl,
    String method,
    String path, {
    Map<String, dynamic>? body,
    bool allowPathFallback = true,
  }) async {
    final normalizedBaseUrl = ApiEndpointConfig.normalizeBaseUrl(baseUrl);
    final encoded = body == null ? null : jsonEncode(body);
    final headers = {'Content-Type': 'application/json'};
    final attempts = <String>[
      path,
      if (allowPathFallback) ..._fallbackPaths(path),
    ];
    ApiHttpException? lastError;

    for (var i = 0; i < attempts.length; i++) {
      final currentPath = attempts[i];
      final uri = _uriForBase(normalizedBaseUrl, currentPath);

      late http.Response response;
      try {
        response = await _performHttp(
          method,
          uri,
          headers: headers,
          encodedBody: encoded,
        );
      } on TimeoutException {
        throw Exception(
          'Tempo esgotado ao conectar com a API em ${uri.toString()}.',
        );
      } catch (e) {
        throw Exception(
          'Falha de conexão com a API em ${uri.toString()}: ${e.toString()}',
        );
      }

      if (response.statusCode >= 200 && response.statusCode < 300) {
        final payload = _decodePayload(response.body);
        if (payload['ok'] != true) {
          throw Exception(payload['error']?.toString() ?? 'erro_desconhecido');
        }
        return payload;
      }

      final bodyPreview = response.body.length > 200
          ? '${response.body.substring(0, 200)}...'
          : response.body;
      final hint = _endpointHint(
        path: currentPath,
        statusCode: response.statusCode,
        body: bodyPreview,
      );
      lastError = ApiHttpException(
        method: method,
        path: currentPath,
        statusCode: response.statusCode,
        url: uri.toString(),
        message: hint,
        responseBody: bodyPreview,
      );

      final isLast = i == attempts.length - 1;
      if (response.statusCode != 404 || isLast) {
        break;
      }
    }

    throw lastError ??
        ApiHttpException(
          method: method,
          path: path,
          statusCode: 0,
          url: _uriForBase(normalizedBaseUrl, path).toString(),
          message: 'Falha desconhecida ao chamar API.',
        );
  }

  Future<Map<String, dynamic>> discoverBackend({
    String? explicitBaseUrl,
  }) async {
    final candidates = ApiEndpointConfig.candidates(
      explicitBaseUrl: explicitBaseUrl,
    );
    final attempts = <Map<String, dynamic>>[];

    for (final candidate in candidates) {
      try {
        final payload = await _requestJsonAtBase(
          candidate.baseUrl,
          'GET',
          '/health',
          allowPathFallback: false,
        );
        _endpoint = candidate;
        return {
          ...payload,
          'reachable': true,
          'base_url': candidate.baseUrl,
          'source': candidate.source,
          'attempts': attempts,
        };
      } catch (e) {
        attempts.add({
          'base_url': candidate.baseUrl,
          'source': candidate.source,
          'error': e.toString().replaceFirst('Exception: ', ''),
        });
      }
    }

    return {
      'ok': false,
      'reachable': false,
      'base_url': _endpoint.baseUrl,
      'source': _endpoint.source,
      'attempts': attempts,
      'message': attempts.isEmpty
          ? 'Nenhum endpoint candidato disponivel.'
          : attempts.first['error'],
    };
  }

  Future<Map<String, dynamic>> getHealthProfile() {
    return _requestJson('GET', '/health');
  }

  Future<Map<String, dynamic>> sendJarvisMessage(
    String message, {
    String userId = 'frontend',
    String mode = 'normal',
    bool autoApprove = false,
  }) async {
    try {
      final payload = await _requestJson(
        'POST',
        '/chat',
        body: {
          'user_id': userId,
          'text': message,
          'mode': mode,
          'auto_approve': autoApprove,
        },
      );
      final reply = payload['reply']?.toString().trim() ?? '';
      if (reply.isNotEmpty &&
          reply.toLowerCase() != 'mensagem vazia.' &&
          reply.toLowerCase() != 'mensagem vazia') {
        return payload;
      }
      return _requestJson('POST', '/chat', body: {'message': message});
    } on ApiHttpException catch (e) {
      if (e.statusCode != 404 && e.statusCode != 400) rethrow;
      return _requestJson('POST', '/chat', body: {'message': message});
    }
  }

  Future<String> sendMessage(String message) async {
    final payload = await sendJarvisMessage(message);
    return payload['reply']?.toString() ?? 'Sem resposta.';
  }

  Future<bool> healthCheck() async {
    final payload = await getHealthProfile();
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

  Future<List<Map<String, dynamic>>> getSessionAudit({
    int limit = 120,
  }) async {
    final lim = limit.clamp(1, 1000);
    final payload =
        await _requestJson('GET', '/security/session-audit?limit=$lim');
    final items = payload['items'];
    if (items is! List) return [];
    return items
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  Future<Map<String, dynamic>> verifySessionAuditChain() {
    return _requestJson('GET', '/security/session-audit/verify');
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

  Future<String> getWeatherByCoords({
    required double latitude,
    required double longitude,
  }) async {
    final suffix =
        '/weather/by-coords?lat=${Uri.encodeComponent(latitude.toString())}&lon=${Uri.encodeComponent(longitude.toString())}';
    final payload = await _requestJson('GET', suffix);
    return payload['summary']?.toString() ?? 'Sem clima por coordenadas.';
  }

  Future<Map<String, dynamic>> getCurrentLocation() async {
    final payload = await _requestJson('GET', '/location/current');
    final loc = payload['location'];
    if (loc is Map<String, dynamic>) return loc;
    if (loc is Map) return Map<String, dynamic>.from(loc);
    return {};
  }

  Future<Map<String, dynamic>> reverseLocation({
    required double latitude,
    required double longitude,
  }) async {
    final suffix =
        '/location/reverse?lat=${Uri.encodeComponent(latitude.toString())}&lon=${Uri.encodeComponent(longitude.toString())}';
    final payload = await _requestJson('GET', suffix);
    return payload;
  }

  Future<Map<String, dynamic>> searchMapPlaces(
    String query, {
    double? latitude,
    double? longitude,
  }) async {
    final buffer =
        StringBuffer('/maps/search?q=${Uri.encodeComponent(query.trim())}');
    if (latitude != null) {
      buffer.write('&lat=${Uri.encodeComponent(latitude.toString())}');
    }
    if (longitude != null) {
      buffer.write('&lon=${Uri.encodeComponent(longitude.toString())}');
    }
    final payload = await _requestJson('GET', buffer.toString());
    return payload;
  }

  Future<Map<String, dynamic>> updateLocation({
    required String label,
    required double latitude,
    required double longitude,
  }) async {
    final payload = await _requestJson(
      'POST',
      '/location/update',
      body: {
        'label': label,
        'latitude': latitude.toStringAsFixed(6),
        'longitude': longitude.toStringAsFixed(6),
      },
    );
    final loc = payload['location'];
    if (loc is Map<String, dynamic>) return loc;
    if (loc is Map) return Map<String, dynamic>.from(loc);
    return {};
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

  Future<Map<String, dynamic>> getObservabilitySummary({
    int window = 200,
  }) async {
    final win = window.clamp(1, 500);
    final payload =
        await _requestJson('GET', '/observability/summary?window=$win');
    final summary = payload['summary'];
    if (summary is Map<String, dynamic>) return summary;
    if (summary is Map) return Map<String, dynamic>.from(summary);
    return {};
  }

  Future<List<Map<String, dynamic>>> getObservabilityTraces({
    int limit = 120,
  }) async {
    final lim = limit.clamp(1, 500);
    final payload =
        await _requestJson('GET', '/observability/traces?limit=$lim');
    final items = payload['items'];
    if (items is! List) return [];
    return items
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  Future<Map<String, dynamic>> agentPlan(String objective) {
    return _requestJson(
      'POST',
      '/agent/plan',
      body: {'objective': objective},
    );
  }

  Future<Map<String, dynamic>> agentExecute(String objective) {
    return _requestJson(
      'POST',
      '/agent/execute',
      body: {'objective': objective},
    );
  }

  Future<Map<String, dynamic>> ragQuery(String query) {
    return _requestJson(
      'POST',
      '/rag/query',
      body: {'query': query},
    );
  }

  Future<Map<String, dynamic>> ragFeedback({
    required String query,
    required String chunkId,
    required int score,
  }) {
    return _requestJson(
      'POST',
      '/rag/feedback',
      body: {
        'query': query,
        'chunk_id': chunkId,
        'score': score,
      },
    );
  }

  Future<Map<String, dynamic>> ragFeedbackStats() {
    return _requestJson('GET', '/rag/feedback/stats');
  }

  Future<Map<String, dynamic>> getSystemStatus() {
    return _requestJson('GET', '/system/status');
  }

  Future<Map<String, dynamic>> getOpsStatus() {
    return _requestJson('GET', '/ops/status');
  }

  Future<Map<String, dynamic>> getSubjectMemory({
    int limit = 8,
  }) {
    final lim = limit.clamp(1, 50);
    return _requestJson('GET', '/memory/subjects?limit=$lim');
  }

  Future<Map<String, dynamic>> getJarvisStatus() {
    return _requestJson('GET', '/jarvis/status');
  }

  Future<List<Map<String, dynamic>>> getRecentMemory({
    String userId = 'frontend',
    int limit = 8,
  }) async {
    final lim = limit.clamp(1, 50);
    final payload = await _requestJson(
      'GET',
      '/memory/recent?user_id=${Uri.encodeComponent(userId)}&limit=$lim',
    );
    final items = payload['items'];
    if (items is! List) return [];
    return items
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  Future<List<Map<String, dynamic>>> searchRecentMemory({
    required String query,
    String userId = 'frontend',
    int limit = 8,
  }) async {
    final lim = limit.clamp(1, 50);
    final payload = await _requestJson(
      'GET',
      '/memory/search?user_id=${Uri.encodeComponent(userId)}&query=${Uri.encodeComponent(query)}&limit=$lim',
    );
    final items = payload['items'];
    if (items is! List) return [];
    return items
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  Future<List<Map<String, dynamic>>> getJarvisTools() async {
    final payload = await _requestJson('GET', '/actions/tools');
    final tools = payload['tools'];
    if (tools is! List) return [];
    return tools
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  Future<Map<String, dynamic>> approveJarvisAction({
    required String toolName,
    required Map<String, dynamic> params,
    String userId = 'frontend',
    String promptText = '',
  }) {
    return _requestJson(
      'POST',
      '/actions/approve',
      body: {
        'user_id': userId,
        'tool_name': toolName,
        'params': params,
        'prompt_text': promptText,
      },
    );
  }

  Future<Map<String, dynamic>> getVoiceStatus() {
    return _requestJson('GET', '/voice/status');
  }

  Future<Map<String, dynamic>> getHelpTopics() {
    return _requestJson('GET', '/help/topics');
  }

  Future<Map<String, dynamic>> getAutonomyStatus() {
    return _requestJson('GET', '/autonomy/status');
  }

  Future<Map<String, dynamic>> getAutonomyConfig() async {
    final payload = await _requestJson('GET', '/autonomy/config');
    final cfg = payload['config'];
    if (cfg is Map<String, dynamic>) return cfg;
    if (cfg is Map) return Map<String, dynamic>.from(cfg);
    return {};
  }

  Future<Map<String, dynamic>> updateAutonomyConfig({
    bool? active,
    String? riskLevel,
    String? freedomLevel,
    bool? confirmSensitive,
  }) async {
    final body = <String, dynamic>{};
    if (active != null) body['active'] = active;
    if (riskLevel != null && riskLevel.trim().isNotEmpty) {
      body['risk_level'] = riskLevel.trim().toLowerCase();
    }
    if (freedomLevel != null && freedomLevel.trim().isNotEmpty) {
      body['freedom_level'] = freedomLevel.trim().toLowerCase();
    }
    if (confirmSensitive != null) {
      body['confirm_sensitive'] = confirmSensitive;
    }
    final payload = await _requestJson('POST', '/autonomy/config', body: body);
    final cfg = payload['config'];
    if (cfg is Map<String, dynamic>) return cfg;
    if (cfg is Map) return Map<String, dynamic>.from(cfg);
    return {};
  }

  Future<Map<String, dynamic>> enqueueAutonomyTask({
    required String objective,
    String source = 'frontend',
  }) async {
    try {
      return await _requestJson(
        'POST',
        '/autonomy/task',
        body: {'objective': objective, 'source': source},
      );
    } on ApiHttpException catch (e) {
      if (e.statusCode == 404) {
        throw Exception(
          'Seu backend atual não possui a rota de autonomia. '
          'Atualize o deploy da API para habilitar o enfileiramento de tarefas.',
        );
      }
      rethrow;
    }
  }

  Future<Map<String, dynamic>> analyzeDocument({
    required String fileName,
    required Uint8List bytes,
    bool? autoLearn,
  }) async {
    final body = <String, dynamic>{
      'filename': fileName,
      'content_base64': base64Encode(bytes),
    };
    if (autoLearn != null) {
      body['auto_learn'] = autoLearn;
    }
    try {
      return await _requestJson(
        'POST',
        '/documents/analyze',
        body: body,
      );
    } on ApiHttpException catch (e) {
      if (e.statusCode == 404) {
        return _buildLocalDocumentFallback(
          fileName: fileName,
          bytes: bytes,
          reason: e.message,
        );
      }
      rethrow;
    }
  }

  Map<String, dynamic> _buildLocalDocumentFallback({
    required String fileName,
    required Uint8List bytes,
    required String reason,
  }) {
    final text = utf8.decode(bytes, allowMalformed: true);
    final normalized = text.replaceAll(RegExp(r'\s+'), ' ').trim();
    final words = normalized.isEmpty ? 0 : normalized.split(' ').length;
    final tokens = RegExp(r'[a-zA-ZÀ-ÿ0-9_]{4,}')
        .allMatches(text.toLowerCase())
        .map((m) => m.group(0) ?? '')
        .where((t) => t.isNotEmpty)
        .toList();
    final freq = <String, int>{};
    for (final t in tokens) {
      freq[t] = (freq[t] ?? 0) + 1;
    }
    final keywords = freq.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    final topKeywords = keywords.take(12).toList();

    final risks = <String>[];
    final riskTokens = {
      'senha',
      'password',
      'token',
      'cpf',
      'rg',
      'cartao',
      'cartão',
      'pix',
      'sigilo',
      'confidencial',
    };
    for (final token in topKeywords.map((e) => e.key)) {
      if (riskTokens.contains(token)) {
        risks.add('Possível dado sensível detectado: "$token".');
      }
    }

    final summary = normalized.isEmpty
        ? 'Arquivo sem texto legível para resumo.'
        : (normalized.length > 420
            ? '${normalized.substring(0, 420)}...'
            : normalized);

    return {
      'ok': true,
      'report': {
        'file_name': fileName,
        'generated_at': DateTime.now().toIso8601String(),
        'stats': {
          'bytes': bytes.length,
          'chars': text.length,
          'words': words,
          'estimated_pages': (words / 450).ceil().clamp(1, 9999),
        },
        'executive_summary': summary,
        'keywords':
            topKeywords.map((e) => {'token': e.key, 'count': e.value}).toList(),
        'risks': risks,
        'sample_excerpts': summary.isEmpty ? [] : [summary],
        'recommendations': [
          'Backend sem endpoint de análise detectado; relatório gerado localmente.',
          'Para aprendizado automático, atualize/deploy a API mais recente.',
        ],
      },
      'learning': {
        'ok': false,
        'skipped': true,
        'local_fallback': true,
        'message': reason,
        'subject_memory': {'subjects': <String>[]},
      },
    };
  }
}
