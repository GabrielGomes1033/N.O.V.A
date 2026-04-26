import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:image/image.dart' as img;

typedef AttachmentOcrExecutor =
    Future<String> Function(
      String fileName,
      Uint8List bytes, {
      String? filePath,
    });

class AttachmentAnalysisService {
  AttachmentAnalysisService({AttachmentOcrExecutor? ocrExecutor})
    : _ocrExecutor = ocrExecutor;

  final AttachmentOcrExecutor? _ocrExecutor;

  static const Set<String> _imageExtensions = {
    'png',
    'jpg',
    'jpeg',
    'webp',
    'bmp',
    'gif',
  };

  bool isImageFileName(String fileName) {
    final normalized = fileName.trim().toLowerCase();
    final dot = normalized.lastIndexOf('.');
    if (dot < 0 || dot == normalized.length - 1) return false;
    return _imageExtensions.contains(normalized.substring(dot + 1));
  }

  Future<Map<String, dynamic>> analyzeImage({
    required String fileName,
    required Uint8List bytes,
    String? filePath,
    bool fromCamera = false,
  }) async {
    final metadata = _extractImageMetadata(fileName: fileName, bytes: bytes);
    final sourceLabel = fromCamera ? 'camera' : 'imagem';
    String recognizedText = '';
    String ocrStatus = 'indisponivel';
    String? ocrMessage;

    try {
      recognizedText = await _recognizeText(
        fileName,
        bytes,
        filePath: filePath,
      );
      if (recognizedText.trim().isNotEmpty) {
        ocrStatus = 'ok';
      } else {
        ocrStatus = 'sem_texto';
        ocrMessage = 'Nenhum texto legível foi identificado na imagem.';
      }
    } catch (e) {
      ocrStatus = 'erro';
      ocrMessage = e.toString().replaceFirst('Exception: ', '');
    }

    return buildLocalImageReport(
      fileName: fileName,
      bytes: bytes,
      recognizedText: recognizedText,
      sourceLabel: sourceLabel,
      metadata: metadata,
      ocrStatus: ocrStatus,
      ocrMessage: ocrMessage,
    );
  }

  @visibleForTesting
  Map<String, dynamic> buildLocalImageReport({
    required String fileName,
    required Uint8List bytes,
    required String recognizedText,
    required String sourceLabel,
    Map<String, dynamic>? metadata,
    String ocrStatus = 'ok',
    String? ocrMessage,
  }) {
    final normalized = recognizedText.replaceAll(RegExp(r'\s+'), ' ').trim();
    final words = normalized.isEmpty ? <String>[] : normalized.split(' ');
    final topKeywords = _topKeywords(normalized);
    final risks = _detectRisks(normalized);
    final excerpts = _sampleExcerpts(normalized);
    final summary = _buildSummary(
      normalized,
      sourceLabel: sourceLabel,
      metadata: metadata ?? const <String, dynamic>{},
    );
    final recommendations = _buildRecommendations(
      normalized,
      sourceLabel: sourceLabel,
      ocrStatus: ocrStatus,
      metadata: metadata ?? const <String, dynamic>{},
    );

    return {
      'ok': true,
      'report': {
        'file_name': fileName,
        'generated_at': DateTime.now().toIso8601String(),
        'analysis_type': 'image',
        'source': sourceLabel,
        'stats': {
          'bytes': bytes.length,
          'chars': normalized.length,
          'words': words.length,
          'estimated_pages': normalized.isEmpty ? 1 : (words.length / 450).ceil().clamp(1, 9999),
        },
        'image': metadata ?? const <String, dynamic>{},
        'executive_summary': summary,
        'keywords': topKeywords,
        'risks': risks,
        'sample_excerpts': excerpts,
        'recommendations': recommendations,
      },
      'learning': {
        'ok': false,
        'skipped': true,
        'local_fallback': true,
        'message':
            ocrMessage ??
            'Análise de imagem realizada localmente no dispositivo.',
        'ocr_status': ocrStatus,
        'subject_memory': {'subjects': <String>[]},
      },
    };
  }

  Future<String> _recognizeText(
    String fileName,
    Uint8List bytes, {
    String? filePath,
  }) async {
    if (_ocrExecutor != null) {
      return _ocrExecutor!(fileName, bytes, filePath: filePath);
    }
    if (kIsWeb || !(Platform.isAndroid || Platform.isIOS)) {
      return '';
    }

    final resolvedPath = await _ensureFilePath(fileName, bytes, filePath: filePath);
    if (resolvedPath == null || resolvedPath.trim().isEmpty) {
      return '';
    }

    final recognizer = TextRecognizer(script: TextRecognitionScript.latin);
    try {
      final inputImage = InputImage.fromFilePath(resolvedPath);
      final recognized = await recognizer.processImage(inputImage);
      return recognized.text.replaceAll(RegExp(r'[ \t]+'), ' ').trim();
    } finally {
      recognizer.close();
    }
  }

  Future<String?> _ensureFilePath(
    String fileName,
    Uint8List bytes, {
    String? filePath,
  }) async {
    final existing = (filePath ?? '').trim();
    if (existing.isNotEmpty) {
      return existing;
    }
    if (kIsWeb) return null;

    final extension = _safeExtension(fileName);
    final temp = File(
      '${Directory.systemTemp.path}/nova_img_${DateTime.now().microsecondsSinceEpoch}$extension',
    );
    await temp.writeAsBytes(bytes, flush: true);
    return temp.path;
  }

  String _safeExtension(String fileName) {
    final trimmed = fileName.trim();
    final dot = trimmed.lastIndexOf('.');
    if (dot >= 0 && dot < trimmed.length - 1) {
      final ext = trimmed.substring(dot).toLowerCase();
      if (ext.length <= 8) return ext;
    }
    return '.jpg';
  }

  Map<String, dynamic> _extractImageMetadata({
    required String fileName,
    required Uint8List bytes,
  }) {
    final format = img.findFormatForData(bytes);
    final decoded = img.decodeImage(bytes);
    final width = decoded?.width ?? 0;
    final height = decoded?.height ?? 0;
    final brightness = _estimateBrightness(decoded);

    return {
      'format': format.name.toUpperCase(),
      'width': width,
      'height': height,
      'orientation': _orientationLabel(width, height),
      if (brightness != null) 'brightness': brightness.toStringAsFixed(1),
      if (brightness != null) 'brightness_label': _brightnessLabel(brightness),
      'extension': _safeExtension(fileName).replaceFirst('.', '').toUpperCase(),
    };
  }

  double? _estimateBrightness(img.Image? decoded) {
    if (decoded == null || decoded.width <= 0 || decoded.height <= 0) {
      return null;
    }
    final stepX = (decoded.width / 24).floor().clamp(1, decoded.width);
    final stepY = (decoded.height / 24).floor().clamp(1, decoded.height);
    var samples = 0;
    var total = 0.0;
    for (var y = 0; y < decoded.height; y += stepY) {
      for (var x = 0; x < decoded.width; x += stepX) {
        total += decoded.getPixel(x, y).luminance.toDouble();
        samples += 1;
      }
    }
    if (samples == 0) return null;
    return total / samples;
  }

  String _orientationLabel(int width, int height) {
    if (width <= 0 || height <= 0) return 'indefinida';
    if (width == height) return 'quadrada';
    return width > height ? 'paisagem' : 'retrato';
  }

  String _brightnessLabel(double brightness) {
    if (brightness < 85) return 'escura';
    if (brightness > 170) return 'clara';
    return 'equilibrada';
  }

  String _buildSummary(
    String recognizedText, {
    required String sourceLabel,
    required Map<String, dynamic> metadata,
  }) {
    final width = metadata['width'];
    final height = metadata['height'];
    final orientation = metadata['orientation'] ?? 'indefinida';

    if (recognizedText.isNotEmpty) {
      final firstSentence = recognizedText.length > 420
          ? '${recognizedText.substring(0, 420)}...'
          : recognizedText;
      return 'Imagem analisada (${sourceLabel == "camera" ? "capturada pela câmera" : "arquivo enviado"}), '
          'com resolução $width x $height e orientação $orientation. '
          'Texto identificado: $firstSentence';
    }

    return 'Imagem analisada (${sourceLabel == "camera" ? "capturada pela câmera" : "arquivo enviado"}), '
        'com resolução $width x $height e orientação $orientation. '
        'Não encontrei texto legível suficiente para gerar um resumo textual.';
  }

  List<Map<String, dynamic>> _topKeywords(String text) {
    if (text.isEmpty) return const [];
    const stop = {
      'para',
      'com',
      'que',
      'uma',
      'como',
      'mais',
      'dos',
      'das',
      'nos',
      'nas',
      'por',
      'seu',
      'sua',
      'sobre',
      'este',
      'esta',
      'isso',
      'essa',
      'http',
      'https',
    };
    final matches = RegExp(r'[a-zA-ZÀ-ÿ0-9_]{4,}')
        .allMatches(text.toLowerCase())
        .map((m) => m.group(0) ?? '')
        .where((token) => token.isNotEmpty && !stop.contains(token));
    final freq = <String, int>{};
    for (final token in matches) {
      freq[token] = (freq[token] ?? 0) + 1;
    }
    final ordered = freq.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    return ordered.take(12).map((e) => {'token': e.key, 'count': e.value}).toList();
  }

  List<String> _detectRisks(String text) {
    final lowered = text.toLowerCase();
    final risks = <String>[];
    final checks = {
      'senha': 'A imagem pode conter senhas ou credenciais.',
      'token': 'A imagem pode conter token ou chave de acesso.',
      'cpf': 'A imagem pode conter dado pessoal sensível (CPF).',
      'cartão': 'A imagem pode conter dado financeiro sensível.',
      'cartao': 'A imagem pode conter dado financeiro sensível.',
      'pix': 'A imagem menciona transação financeira via PIX.',
      'banco': 'A imagem parece conter contexto bancário ou comprovante.',
      'comprovante': 'A imagem parece ser um comprovante ou recibo.',
      'confidencial': 'A imagem traz marcação de conteúdo confidencial.',
    };
    checks.forEach((token, message) {
      if (lowered.contains(token)) {
        risks.add(message);
      }
    });
    return risks;
  }

  List<String> _sampleExcerpts(String text) {
    if (text.isEmpty) return const [];
    final excerpts = <String>[];
    for (final part in reSplitSentences(text)) {
      final cleaned = part.trim();
      if (cleaned.length >= 24) {
        excerpts.add(cleaned.length > 280 ? '${cleaned.substring(0, 280)}...' : cleaned);
      }
      if (excerpts.length >= 4) break;
    }
    return excerpts;
  }

  List<String> _buildRecommendations(
    String recognizedText, {
    required String sourceLabel,
    required String ocrStatus,
    required Map<String, dynamic> metadata,
  }) {
    final out = <String>[
      'Revise manualmente o texto reconhecido antes de compartilhar ou arquivar.',
    ];
    if (recognizedText.isEmpty || ocrStatus != 'ok') {
      out.add(
        sourceLabel == 'camera'
            ? 'Tente fotografar novamente com mais luz, foco e enquadramento reto.'
            : 'Se a imagem estiver pequena ou desfocada, tente reenviar uma versão mais nítida.',
      );
    } else {
      out.add('Se quiser, use esse conteúdo para gerar um resumo mais específico no chat.');
    }

    final brightness = double.tryParse('${metadata['brightness'] ?? ''}');
    if (brightness != null && brightness < 85) {
      out.add('A imagem parece escura; aumente a iluminação para melhorar a leitura.');
    }
    if ((metadata['orientation'] ?? '') == 'paisagem' && recognizedText.isEmpty) {
      out.add('Se for um documento, tente capturar em modo retrato para melhorar o OCR.');
    }
    out.add('Para aprendizado automático no backend, mantenha também a análise de documentos autenticada.');
    return out;
  }
}

List<String> reSplitSentences(String text) {
  return text.split(RegExp(r'(?<=[.!?])\s+'));
}
