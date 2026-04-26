import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend_flutter/services/chat_api.dart';
import 'package:http/http.dart' as http;

void main() {
  test('envia X-API-Key quando token da API esta configurado', () async {
    Map<String, String>? capturedHeaders;

    final service = ChatApiService(
      baseUrl: 'http://127.0.0.1:8000',
      apiToken: 'segredo-api',
      httpExecutor: (
        String method,
        Uri uri, {
        required Map<String, String> headers,
        String? encodedBody,
      }) async {
        capturedHeaders = Map<String, String>.from(headers);
        expect(method, 'GET');
        expect(uri.toString(), 'http://127.0.0.1:8000/ops/status');
        return http.Response(jsonEncode({'ok': true}), 200);
      },
    );

    final payload = await service.getOpsStatus();

    expect(payload['ok'], isTrue);
    expect(capturedHeaders?['X-API-Key'], 'segredo-api');
  });

  test('nao envia X-API-Key quando token da API esta vazio', () async {
    Map<String, String>? capturedHeaders;

    final service = ChatApiService(
      baseUrl: 'http://127.0.0.1:8000',
      httpExecutor: (
        String method,
        Uri uri, {
        required Map<String, String> headers,
        String? encodedBody,
      }) async {
        capturedHeaders = Map<String, String>.from(headers);
        expect(uri.toString(), 'http://127.0.0.1:8000/health');
        return http.Response(jsonEncode({'ok': true}), 200);
      },
    );

    final payload = await service.getHealthProfile();

    expect(payload['ok'], isTrue);
    expect(capturedHeaders?.containsKey('X-API-Key'), isFalse);
  });

  test('updateApiToken autentica chamadas seguintes', () async {
    Map<String, String>? capturedHeaders;

    final service = ChatApiService(
      baseUrl: 'http://127.0.0.1:8000',
      httpExecutor: (
        String method,
        Uri uri, {
        required Map<String, String> headers,
        String? encodedBody,
      }) async {
        capturedHeaders = Map<String, String>.from(headers);
        expect(uri.toString(), 'http://127.0.0.1:8000/system/status');
        return http.Response(jsonEncode({'ok': true}), 200);
      },
    );

    service.updateApiToken('novo-token');
    final payload = await service.getSystemStatus();

    expect(payload['ok'], isTrue);
    expect(capturedHeaders?['X-API-Key'], 'novo-token');
  });
}
