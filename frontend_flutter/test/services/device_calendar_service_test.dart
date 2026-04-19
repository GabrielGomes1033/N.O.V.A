import 'package:flutter_test/flutter_test.dart';

import 'package:frontend_flutter/services/device_calendar_service.dart';

void main() {
  final service = DeviceCalendarService();

  test('detecta pedido de agenda com linguagem natural', () {
    expect(
      DeviceCalendarService.looksLikeCalendarRequest(
        'Agende reuniao com cliente amanha as 15h',
      ),
      isTrue,
    );
  });

  test('parseia evento com horario natural e duracao padrao', () {
    final parsed = service.parseRequest(
      'Agende reuniao com cliente amanha as 15h',
      now: DateTime(2026, 4, 23, 10, 0),
    );

    expect(parsed['ok'], isTrue);
    expect(parsed['title'], 'reuniao com cliente');
    expect(parsed['start_at'], DateTime(2026, 4, 24, 15, 0));
    expect(parsed['end_at'], DateTime(2026, 4, 24, 16, 0));
  });

  test('parseia evento com data e horario final explicitos', () {
    final parsed = service.parseRequest(
      'Marque foco de estudos em 2026-05-01 19:00 ate 20:30',
      now: DateTime(2026, 4, 23, 10, 0),
    );

    expect(parsed['ok'], isTrue);
    expect(parsed['title'], 'foco de estudos');
    expect(parsed['start_at'], DateTime(2026, 5, 1, 19, 0));
    expect(parsed['end_at'], DateTime(2026, 5, 1, 20, 30));
  });
}
