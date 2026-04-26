import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend_flutter/services/attachment_analysis_service.dart';

void main() {
  test('classifica extensao de imagem corretamente', () {
    final service = AttachmentAnalysisService();

    expect(service.isImageFileName('foto.png'), isTrue);
    expect(service.isImageFileName('recibo.JPG'), isTrue);
    expect(service.isImageFileName('contrato.pdf'), isFalse);
  });

  test('gera relatorio local de imagem com OCR e metadados', () {
    final service = AttachmentAnalysisService();

    final payload = service.buildLocalImageReport(
      fileName: 'comprovante.png',
      bytes: Uint8List.fromList(List<int>.generate(16, (i) => i)),
      recognizedText: 'Comprovante PIX Banco valor total 120 reais.',
      sourceLabel: 'camera',
      metadata: {
        'format': 'PNG',
        'width': 1080,
        'height': 1920,
        'orientation': 'retrato',
        'brightness': '142.0',
        'brightness_label': 'equilibrada',
      },
      ocrStatus: 'ok',
    );

    expect(payload['ok'], isTrue);
    final report = Map<String, dynamic>.from(payload['report'] as Map);
    expect(report['analysis_type'], 'image');
    expect(report['source'], 'camera');
    expect((report['executive_summary'] as String).toLowerCase(), contains('texto identificado'));
    expect((report['risks'] as List).join(' ').toLowerCase(), contains('pix'));
    expect(report['keywords'], isNotEmpty);
  });
}
