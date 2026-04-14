import 'dart:convert';

import 'package:crypto/crypto.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SecureSecretsService {
  static const _kTelegramToken = 'nova.telegram.token';
  static const _kTelegramChatId = 'nova.telegram.chat_id';
  static const _kAdminPinHash = 'nova.admin.pin_hash';

  final FlutterSecureStorage _storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  Future<Map<String, String>> readConfigSecrets() async {
    final token = await _storage.read(key: _kTelegramToken) ?? '';
    final chatId = await _storage.read(key: _kTelegramChatId) ?? '';
    return {
      'telegram_token': token,
      'telegram_chat_id': chatId,
    };
  }

  Future<void> saveConfigSecrets({
    required String telegramToken,
    required String telegramChatId,
  }) async {
    await _storage.write(key: _kTelegramToken, value: telegramToken.trim());
    await _storage.write(key: _kTelegramChatId, value: telegramChatId.trim());
  }

  Future<bool> hasAdminPin() async {
    final h = await _storage.read(key: _kAdminPinHash);
    return (h ?? '').isNotEmpty;
  }

  Future<void> setAdminPin(String pin) async {
    final hash = _pinHash(pin);
    await _storage.write(key: _kAdminPinHash, value: hash);
  }

  Future<bool> validateAdminPin(String pin) async {
    final saved = await _storage.read(key: _kAdminPinHash) ?? '';
    if (saved.isEmpty) return false;
    return saved == _pinHash(pin);
  }

  Future<void> clearAdminPin() async {
    await _storage.delete(key: _kAdminPinHash);
  }

  String _pinHash(String pin) {
    final normalized = pin.trim();
    final bytes = utf8.encode('nova::$normalized::v1');
    return sha256.convert(bytes).toString();
  }
}
