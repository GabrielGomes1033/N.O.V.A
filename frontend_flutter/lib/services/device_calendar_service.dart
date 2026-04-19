import 'dart:async';

import 'package:flutter/services.dart';

import 'platform_capabilities.dart';

class DeviceCalendarService {
  static const MethodChannel _channel = MethodChannel('nova/device_calendar');

  static const Map<String, int> _weekdayMap = {
    'segunda': DateTime.monday,
    'segunda-feira': DateTime.monday,
    'terca': DateTime.tuesday,
    'terça': DateTime.tuesday,
    'terca-feira': DateTime.tuesday,
    'terça-feira': DateTime.tuesday,
    'quarta': DateTime.wednesday,
    'quarta-feira': DateTime.wednesday,
    'quinta': DateTime.thursday,
    'quinta-feira': DateTime.thursday,
    'sexta': DateTime.friday,
    'sexta-feira': DateTime.friday,
    'sabado': DateTime.saturday,
    'sábado': DateTime.saturday,
    'domingo': DateTime.sunday,
  };

  bool get supportsNativeCalendar => PlatformCapabilities.isAndroid;

  static String _clean(String text) {
    return text.replaceAll(RegExp(r'\s+'), ' ').trim();
  }

  static String _normalizeNaturalTimes(String text) {
    var normalized = _clean(text);
    normalized = normalized.replaceAllMapped(
      RegExp(r'\b(\d{1,2})h(\d{2})?\b', caseSensitive: false),
      (match) {
        final hour = int.tryParse(match.group(1) ?? '') ?? 0;
        final minute = int.tryParse(match.group(2) ?? '0') ?? 0;
        return '${hour.toString().padLeft(2, '0')}:${minute.toString().padLeft(2, '0')}';
      },
    );
    normalized = normalized.replaceAllMapped(
      RegExp(r'\b(\d{1,2})\s*horas?\b', caseSensitive: false),
      (match) {
        final hour = int.tryParse(match.group(1) ?? '') ?? 0;
        return '${hour.toString().padLeft(2, '0')}:00';
      },
    );
    return normalized;
  }

  static bool looksLikeCalendarRequest(String text) {
    final normalized = _normalizeNaturalTimes(text).toLowerCase();
    if (normalized.isEmpty) return false;
    final hasScheduleVerb = RegExp(
      r'\b(?:agende|agendar|agendamento|marque|marcar|adicione|adicionar|coloque|colocar|crie|criar)\b',
      caseSensitive: false,
    ).hasMatch(normalized);
    if (!hasScheduleVerb) return false;
    final hasEventHint = [
      'agenda',
      'evento',
      'compromisso',
      'reuniao',
      'reunião',
      'tarefa',
      'google agenda',
      'google calendar',
    ].any(normalized.contains);
    final hasTimeMarker = RegExp(
      r'\b(?:amanha|amanhã|hoje|segunda|segunda-feira|terca|terça|quarta|quinta|sexta|sabado|sábado|domingo)\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}\b',
      caseSensitive: false,
    ).hasMatch(normalized);
    return hasTimeMarker || hasEventHint;
  }

  DateTime _parseDate(String value, DateTime baseNow) {
    final dateText = _clean(value).toLowerCase();
    if (dateText == 'hoje') {
      return DateTime(baseNow.year, baseNow.month, baseNow.day);
    }
    if (dateText == 'amanha' || dateText == 'amanhã') {
      final tomorrow = baseNow.add(const Duration(days: 1));
      return DateTime(tomorrow.year, tomorrow.month, tomorrow.day);
    }
    if (_weekdayMap.containsKey(dateText)) {
      final targetWeekday = _weekdayMap[dateText]!;
      var delta = targetWeekday - baseNow.weekday;
      if (delta <= 0) delta += 7;
      final target = baseNow.add(Duration(days: delta));
      return DateTime(target.year, target.month, target.day);
    }
    if (RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(dateText)) {
      final parts = dateText.split('-');
      return DateTime(
        int.parse(parts[0]),
        int.parse(parts[1]),
        int.parse(parts[2]),
      );
    }
    if (RegExp(r'^\d{1,2}/\d{1,2}/\d{2,4}$').hasMatch(dateText)) {
      final parts = dateText.split('/');
      var year = int.parse(parts[2]);
      if (year < 100) year += 2000;
      return DateTime(year, int.parse(parts[1]), int.parse(parts[0]));
    }
    throw const FormatException('date_not_supported');
  }

  ({int hour, int minute}) _parseTime(String value) {
    final parts = _clean(value).split(':');
    return (
      hour: int.parse(parts[0]),
      minute: int.parse(parts[1]),
    );
  }

  int _extractDurationMinutes(String text) {
    final normalized = _normalizeNaturalTimes(text).toLowerCase();
    final minuteMatch = RegExp(
      r'\bpor\s+(\d{1,3})\s*(min|minuto|minutos)\b',
      caseSensitive: false,
    ).firstMatch(normalized);
    if (minuteMatch != null) {
      final value = int.tryParse(minuteMatch.group(1) ?? '') ?? 60;
      return value < 5 ? 5 : value;
    }
    final hourMatch = RegExp(
      r'\bpor\s+(\d{1,2})\s*(h|hora|horas)\b',
      caseSensitive: false,
    ).firstMatch(normalized);
    if (hourMatch != null) {
      final value = int.tryParse(hourMatch.group(1) ?? '') ?? 1;
      final minutes = value * 60;
      return minutes < 15 ? 15 : minutes;
    }
    return 60;
  }

  Map<String, dynamic> _extractDateTimeWindow(String text, DateTime baseNow) {
    final raw = _normalizeNaturalTimes(text);
    final patterns = <RegExp>[
      RegExp(
        r'(?<date>\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|amanha|amanhã|hoje|segunda(?:-feira)?|terca(?:-feira)?|terça(?:-feira)?|quarta(?:-feira)?|quinta(?:-feira)?|sexta(?:-feira)?|sabado|sábado|domingo)\s*(?:as|às)?\s*(?<start>\d{1,2}:\d{2})(?:\s*(?:ate|até|a)\s*(?<end>\d{1,2}:\d{2}))?',
        caseSensitive: false,
      ),
      RegExp(
        r'(?<start>\d{1,2}:\d{2})\s*(?:ate|até|a)\s*(?<end>\d{1,2}:\d{2})\s*(?:de\s+)?(?<date>\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|amanha|amanhã|hoje|segunda(?:-feira)?|terca(?:-feira)?|terça(?:-feira)?|quarta(?:-feira)?|quinta(?:-feira)?|sexta(?:-feira)?|sabado|sábado|domingo)',
        caseSensitive: false,
      ),
      RegExp(
        r'(?<date>\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|amanha|amanhã|hoje|segunda(?:-feira)?|terca(?:-feira)?|terça(?:-feira)?|quarta(?:-feira)?|quinta(?:-feira)?|sexta(?:-feira)?|sabado|sábado|domingo)',
        caseSensitive: false,
      ),
      RegExp(
        r'(?:as|às)\s*(?<start>\d{1,2}:\d{2})(?:\s*(?:ate|até|a)\s*(?<end>\d{1,2}:\d{2}))?',
        caseSensitive: false,
      ),
    ];

    for (final pattern in patterns) {
      final match = pattern.firstMatch(raw);
      if (match == null) continue;
      final dateText = _clean(match.namedGroup('date') ?? '');
      var startText = _clean(match.namedGroup('start') ?? '');
      final endText = _clean(match.namedGroup('end') ?? '');
      var assumedDate = false;
      late DateTime startAt;

      if (dateText.isEmpty) {
        if (startText.isEmpty) continue;
        final parsedTime = _parseTime(startText);
        startAt = DateTime(
          baseNow.year,
          baseNow.month,
          baseNow.day,
          parsedTime.hour,
          parsedTime.minute,
        );
        if (!startAt.isAfter(baseNow)) {
          startAt = startAt.add(const Duration(days: 1));
        }
        assumedDate = true;
      } else {
        final dateValue = _parseDate(dateText, baseNow);
        if (startText.isEmpty) {
          startText = '09:00';
          assumedDate = true;
        }
        final parsedTime = _parseTime(startText);
        startAt = DateTime(
          dateValue.year,
          dateValue.month,
          dateValue.day,
          parsedTime.hour,
          parsedTime.minute,
        );
      }

      late DateTime endAt;
      if (endText.isNotEmpty) {
        final parsedEnd = _parseTime(endText);
        endAt = DateTime(
          startAt.year,
          startAt.month,
          startAt.day,
          parsedEnd.hour,
          parsedEnd.minute,
        );
        if (!endAt.isAfter(startAt)) {
          endAt = endAt.add(const Duration(days: 1));
        }
      } else {
        endAt = startAt.add(Duration(minutes: _extractDurationMinutes(raw)));
      }

      return {
        'start_at': startAt,
        'end_at': endAt,
        'matched_text': match.group(0) ?? '',
        'assumed_date': assumedDate,
      };
    }

    throw const FormatException('date_time_not_found');
  }

  String _stripSchedulePrefix(String text) {
    var stripped = _clean(text);
    stripped = stripped.replaceFirst(
      RegExp(r'^(?:nova[\s,:-]+)?', caseSensitive: false),
      '',
    );
    stripped = stripped.replaceFirst(
      RegExp(
        r'^(?:agende|agendar|agenda|marque|marcar|crie|criar|adicione|adicionar|coloque)\s+(?:(?:um|uma)\s+)?(?:(?:na|no)\s+(?:agenda(?:\s+do\s+google)?|google\s+calendar|google\s+agenda)\s+)?',
        caseSensitive: false,
      ),
      '',
    );
    return stripped.replaceAll(RegExp(r'^[ ,:-]+|[ ,:-]+$'), '').trim();
  }

  Map<String, dynamic> parseRequest(String requestText, {DateTime? now}) {
    final raw = _normalizeNaturalTimes(_clean(requestText));
    if (raw.isEmpty) {
      return {
        'ok': false,
        'error': 'request_text_required',
        'message': 'Me diga o que devo agendar.',
      };
    }

    final baseNow = now ?? DateTime.now();
    late Map<String, dynamic> window;
    try {
      window = _extractDateTimeWindow(raw, baseNow);
    } catch (_) {
      return {
        'ok': false,
        'error': 'date_time_not_found',
        'message':
            'Nao consegui identificar data e hora. Exemplo: agende reuniao com cliente amanha as 15:00',
      };
    }

    var title = _stripSchedulePrefix(raw);
    final matched = _clean(window['matched_text']?.toString() ?? '');
    if (matched.isNotEmpty) {
      title = title.replaceFirst(matched, ' ').trim();
    }
    title = title.replaceFirst(
      RegExp(
        r'\b(?:na agenda(?: do google)?|no google calendar|na google agenda)\b',
        caseSensitive: false,
      ),
      ' ',
    );
    title = title.replaceFirst(
      RegExp(r'\b(?:em|para|de|no|na)\s*$', caseSensitive: false),
      ' ',
    );
    title = _clean(title).replaceAll(RegExp(r'^[ ,:-]+|[ ,:-]+$'), '').trim();
    if (title.isEmpty) {
      title = 'Compromisso';
    }

    final assumptions = <String>[];
    if (window['assumed_date'] == true) {
      assumptions.add(
        'Sem data explicita, usei a proxima ocorrencia compativel.',
      );
    }
    if (_extractDurationMinutes(raw) == 60 &&
        !RegExp(r'\b(?:ate|até|a)\s+\d{1,2}:\d{2}\b', caseSensitive: false)
            .hasMatch(raw)) {
      assumptions.add(
        'Como voce nao informou horario final, usei duracao padrao de 1 hora.',
      );
    }

    return {
      'ok': true,
      'title': title,
      'description': 'Pedido original: $raw',
      'start_at': window['start_at'],
      'end_at': window['end_at'],
      'assumptions': assumptions,
      'request_text': raw,
    };
  }

  Future<Map<String, dynamic>> createEvent({
    required String title,
    required DateTime startAt,
    required DateTime endAt,
    String description = '',
    String location = '',
    String preferredEmail = '',
  }) async {
    if (!supportsNativeCalendar) {
      return {
        'ok': false,
        'error': 'platform_not_supported',
        'message':
            'A criacao direta de eventos no dispositivo esta disponivel no Android.',
      };
    }

    try {
      final payload = await _channel.invokeMethod<dynamic>('createEvent', {
        'title': title.trim(),
        'description': description.trim(),
        'location': location.trim(),
        'startMillis': startAt.millisecondsSinceEpoch,
        'endMillis': endAt.millisecondsSinceEpoch,
        'timezone': '',
        'preferredEmail': preferredEmail.trim(),
      });
      if (payload is Map) {
        return Map<String, dynamic>.from(payload);
      }
      return {
        'ok': false,
        'error': 'invalid_native_payload',
        'message': 'Resposta invalida do calendario do dispositivo.',
      };
    } on PlatformException catch (error) {
      return {
        'ok': false,
        'error': error.code,
        'message': error.message ?? 'Falha ao criar evento no calendario.',
      };
    } catch (error) {
      return {
        'ok': false,
        'error': 'calendar_unknown_error',
        'message': error.toString(),
      };
    }
  }
}
