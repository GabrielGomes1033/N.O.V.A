import 'dart:convert';
import 'dart:io';

import 'package:audioplayers/audioplayers.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:image_picker/image_picker.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:url_launcher/url_launcher.dart';

import '../services/chat_api.dart';
import '../services/background_wake_service.dart';
import '../services/app_security_service.dart';
import '../services/device_connectivity.dart';
import '../services/local_database.dart';
import '../services/platform_capabilities.dart';
import '../services/reminder_notifications.dart';
import '../services/secure_secrets_service.dart';
import '../services/system_scan_service.dart';
import '../widgets/home/chat_shell_widgets.dart';
import '../widgets/home/dialog_widgets.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> with WidgetsBindingObserver {
  final TextEditingController _messageController = TextEditingController();
  final SpeechToText _speech = SpeechToText();
  final FlutterTts _tts = FlutterTts();
  final ChatApiService _api = ChatApiService();
  final LocalDatabaseService _localDb = LocalDatabaseService();
  final DeviceConnectivityService _deviceConnectivity =
      DeviceConnectivityService();
  final AppSecurityService _appSecurity = AppSecurityService();
  final SecureSecretsService _secureSecrets = SecureSecretsService();
  final AudioPlayer _audioPlayer = AudioPlayer();
  final AudioPlayer _voicePlayer = AudioPlayer();
  final ImagePicker _imagePicker = ImagePicker();
  final ReminderNotificationsService _notifications =
      ReminderNotificationsService();
  final SystemScanService _systemScan = SystemScanService();

  final List<NovaChatLine> _chat = [];
  List<Map<String, dynamic>> _knowledge = [];
  List<Map<String, dynamic>> _users = [];
  Map<String, dynamic> _config = {
    'voz_ativa': true,
    'voice_neural_hybrid': true,
    'voice_profile': 'feminina',
    'escuta_ativa': true,
    'wake_word': 'nova',
    'continuous_wake': false,
    'push_to_talk_only': true,
    'telegram_ativo': false,
    'telegram_token': '',
    'telegram_chat_id': '',
    'autonomia_ativa': true,
    'autonomia_nivel_risco': 'alto',
    'autonomia_liberdade': 'alta',
    'autonomia_requer_confirmacao_sensivel': false,
    'auto_document_learning': true,
    'admin_guard': false,
    'allow_voice_on_lock': true,
    'log_consciencia': <dynamic>[],
  };

  String _systemStatus = 'Conectando...';
  bool _speechReady = false;
  bool _isListening = false;
  bool _executedFromVoice = false;
  bool _sending = false;
  bool _loadingState = false;
  String? _composerAttachmentName;
  bool _continuousWakeMode = false;
  bool _manualListeningStop = false;
  int _speakRequestId = 0;
  bool _adminUnlocked = false;
  DateTime? _adminUnlockedAt;
  List<Map<String, String>> _musicLibrary = [];
  List<Map<String, dynamic>> _reminders = [];
  Map<String, dynamic> _jarvisStatus = {};
  Map<String, dynamic> _voiceStatus = {};
  List<Map<String, dynamic>> _jarvisTools = [];
  List<Map<String, dynamic>> _recentMemory = [];

  bool get _listenModeEnabled => _config['escuta_ativa'] != false;
  bool get _pushToTalkOnly => _config['push_to_talk_only'] != false;
  bool get _effectiveContinuousWake => !_pushToTalkOnly && _continuousWakeMode;

  String _periodGreeting() {
    final h = DateTime.now().hour;
    if (h >= 5 && h < 12) return 'Bom dia';
    if (h >= 12 && h < 18) return 'Boa tarde';
    return 'Boa noite';
  }

  String _initialGreeting() {
    final base = '${_periodGreeting()}! Eu sou a NOVA.';
    return '$base Estou aqui, pronta para aprender com você e te ajudar.';
  }

  String _jarvisUserId() {
    final named = (_config['nome_usuario']?.toString().trim() ?? '');
    if (named.isNotEmpty) return named;
    return 'frontend';
  }

  String _truncateRailText(String text, {int limit = 82}) {
    final normalized = text.replaceAll(RegExp(r'\s+'), ' ').trim();
    if (normalized.length <= limit) return normalized;
    final cut = normalized.substring(0, limit);
    final safe =
        cut.contains(' ') ? cut.substring(0, cut.lastIndexOf(' ')) : cut;
    return '${safe.trim()}...';
  }

  List<String> _memoryRailItems() {
    return _recentMemory
        .map((item) {
          final category = item['category']?.toString().trim() ?? 'contexto';
          final content = item['content']?.toString().trim() ?? '';
          if (content.isEmpty) return '';
          return '${category.toUpperCase()}: ${_truncateRailText(content)}';
        })
        .where((item) => item.isNotEmpty)
        .toList();
  }

  Future<void> _refreshJarvisFoundation() async {
    Map<String, dynamic> jarvisStatus = _jarvisStatus;
    Map<String, dynamic> voiceStatus = _voiceStatus;
    List<Map<String, dynamic>> tools = _jarvisTools;
    List<Map<String, dynamic>> recentMemory = _recentMemory;

    try {
      jarvisStatus = await _api.getJarvisStatus();
    } catch (_) {}

    try {
      voiceStatus = await _api.getVoiceStatus();
    } catch (_) {}

    try {
      tools = await _api.getJarvisTools();
    } catch (_) {}

    try {
      recentMemory = await _api.getRecentMemory(
        userId: _jarvisUserId(),
        limit: 6,
      );
    } catch (_) {}

    if (!mounted) return;
    setState(() {
      _jarvisStatus = jarvisStatus;
      _voiceStatus = voiceStatus;
      _jarvisTools = tools;
      _recentMemory = recentMemory;
    });
  }

  Future<Uint8List> _buildDocumentReportPdf({
    required String reportText,
    required String fileName,
  }) async {
    final doc = pw.Document();
    final now = DateTime.now().toIso8601String();
    final sanitized = fileName.trim().isEmpty ? 'documento' : fileName.trim();

    doc.addPage(
      pw.MultiPage(
        pageTheme: pw.PageTheme(
          margin: const pw.EdgeInsets.all(24),
          theme: pw.ThemeData.withFont(
            base: await PdfGoogleFonts.openSansRegular(),
            bold: await PdfGoogleFonts.openSansBold(),
          ),
        ),
        build: (context) => [
          pw.Text(
            'NOVA • Relatório de Documento',
            style: pw.TextStyle(
              fontSize: 20,
              fontWeight: pw.FontWeight.bold,
              color: PdfColors.blue900,
            ),
          ),
          pw.SizedBox(height: 8),
          pw.Text('Arquivo: $sanitized',
              style:
                  const pw.TextStyle(fontSize: 11, color: PdfColors.grey700)),
          pw.Text('Gerado em: $now',
              style:
                  const pw.TextStyle(fontSize: 11, color: PdfColors.grey700)),
          pw.SizedBox(height: 12),
          pw.Container(
            padding: const pw.EdgeInsets.all(12),
            decoration: pw.BoxDecoration(
              border: pw.Border.all(color: PdfColors.blue200),
              color: PdfColors.blue50,
              borderRadius: pw.BorderRadius.circular(6),
            ),
            child: pw.Text(
              reportText.trim().isEmpty
                  ? 'Relatório vazio.'
                  : reportText.trim(),
              style: const pw.TextStyle(
                fontSize: 11.5,
                lineSpacing: 2,
                color: PdfColors.black,
              ),
            ),
          ),
        ],
      ),
    );
    return doc.save();
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _chat.add(NovaChatLine(fromUser: false, text: _initialGreeting()));
    _restoreLocalState();
    _initTts();
    _initSpeech();
    _refreshAdminState();
    _loadMusicLibrary();
    _loadReminders();
    _notifications.init();
    _refreshJarvisFoundation();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _tts.stop();
    _audioPlayer.dispose();
    _voicePlayer.dispose();
    BackgroundWakeService.stop();
    _localDb.close();
    _messageController.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    super.didChangeAppLifecycleState(state);
    if (!PlatformCapabilities.isAndroid) return;

    if (state == AppLifecycleState.resumed) {
      BackgroundWakeService.stop();
      if (_listenModeEnabled && _effectiveContinuousWake && !_isListening) {
        _manualListeningStop = false;
        _startListening();
      }
      return;
    }

    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.inactive) {
      if (_listenModeEnabled && _effectiveContinuousWake) {
        _manualListeningStop = true;
        _speech.stop();
        final wake = _config['wake_word']?.toString() ?? 'nova';
        final allow = _config['allow_voice_on_lock'] != false;
        BackgroundWakeService.start(
          wakeWord: wake,
          allowVoiceOnLock: allow,
        );
      }
    }
  }

  Future<void> _restoreLocalState() async {
    try {
      final decoded = await _localDb.loadAdminState();
      final secureConfig = await _secureSecrets.readConfigSecrets();

      final knowledge = decoded['knowledge'];
      final users = decoded['users'];
      final config = decoded['config'];

      if (!mounted) return;
      setState(() {
        if (knowledge is List) {
          _knowledge = knowledge
              .whereType<Map>()
              .map((item) => Map<String, dynamic>.from(item))
              .toList();
        }
        if (users is List) {
          _users = users
              .whereType<Map>()
              .map((item) => Map<String, dynamic>.from(item))
              .toList();
        }
        if (config is Map) {
          _config = {
            ..._config,
            ...Map<String, dynamic>.from(config),
            ...secureConfig,
          };
          _continuousWakeMode = _config['continuous_wake'] != false;
          if (_pushToTalkOnly) {
            _continuousWakeMode = false;
          }
        }
      });
      if (!_listenModeEnabled) {
        _manualListeningStop = true;
        await _speech.stop();
        await BackgroundWakeService.stop();
        if (mounted) {
          setState(() => _isListening = false);
        }
      }
    } catch (_) {
      // Ignora estado local inválido.
    }
  }

  Future<void> _saveLocalState() async {
    await _secureSecrets.saveConfigSecrets(
      telegramToken: _config['telegram_token']?.toString() ?? '',
      telegramChatId: _config['telegram_chat_id']?.toString() ?? '',
    );

    final sanitizedConfig = Map<String, dynamic>.from(_config)
      ..remove('telegram_token')
      ..remove('telegram_chat_id');

    await _localDb.saveAdminState(
      knowledge: _knowledge,
      users: _users,
      config: sanitizedConfig,
    );
  }

  Future<void> _refreshAdminState() async {
    if (_loadingState) return;
    _loadingState = true;
    try {
      final payload = await _api.getAdminState();
      final state = payload['state'];
      if (state is Map) {
        if (!mounted) return;
        setState(() {
          _knowledge = (state['knowledge'] is List)
              ? (state['knowledge'] as List)
                  .whereType<Map>()
                  .map((item) => Map<String, dynamic>.from(item))
                  .toList()
              : _knowledge;
          _users = (state['users'] is List)
              ? (state['users'] as List)
                  .whereType<Map>()
                  .map((item) => Map<String, dynamic>.from(item))
                  .toList()
              : _users;
          _config = (state['config'] is Map)
              ? {
                  ..._config,
                  ...Map<String, dynamic>.from(state['config']),
                }
              : _config;
          _continuousWakeMode = _config['continuous_wake'] != false;
          if (_pushToTalkOnly) {
            _continuousWakeMode = false;
          }
          _systemStatus = 'Painel sincronizado com backend.';
        });
        await _saveLocalState();
      }
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _systemStatus =
            'Sem conexão com backend. Usando dados locais do celular.';
      });
    } finally {
      _loadingState = false;
    }
  }

  Future<void> _loadMusicLibrary() async {
    if (!PlatformCapabilities.supportsLocalMusicLibrary) {
      if (!mounted) return;
      setState(() => _musicLibrary = []);
      return;
    }
    try {
      final items = await _localDb.getMusicLibrary();
      if (!mounted) return;
      setState(() => _musicLibrary = items);
    } catch (_) {
      // ignora falha local
    }
  }

  Future<void> _loadReminders() async {
    try {
      final items = await _api.getReminders();
      if (!mounted) return;
      setState(() => _reminders = items);
      await _syncReminderNotifications(items);
      try {
        await _localDb.saveReminders(items);
      } catch (_) {
        // Em plataformas sem DB local (ex.: web), mantém dados do backend.
      }
      return;
    } catch (_) {
      // fallback local apenas se backend falhar
    }
    try {
      final localItems = await _localDb.getReminders();
      if (!mounted) return;
      setState(() => _reminders = localItems);
      await _syncReminderNotifications(localItems);
    } catch (_) {
      // mantém último estado em memória
    }
  }

  int _notificationIdFromReminderId(String id) {
    var hash = 0;
    for (final code in id.codeUnits) {
      hash = ((hash * 31) + code) & 0x7fffffff;
    }
    return hash == 0 ? 1 : hash;
  }

  DateTime? _parseReminderWhen(String raw) {
    final txt = raw.trim();
    if (txt.isEmpty) return null;
    try {
      return DateTime.parse(txt).toLocal();
    } catch (_) {
      return null;
    }
  }

  Future<void> _syncReminderNotifications(
      List<Map<String, dynamic>> items) async {
    for (final item in items) {
      final id = (item['id'] ?? '').toString().trim();
      final texto = (item['texto'] ?? '').toString().trim();
      final whenRaw = (item['quando'] ?? '').toString();
      if (id.isEmpty || texto.isEmpty) continue;
      final when = _parseReminderWhen(whenRaw);
      if (when == null) continue;
      final now = DateTime.now();
      if (!when.isAfter(now)) continue;
      final notifId = _notificationIdFromReminderId(id);
      try {
        await _notifications.scheduleReminder(
          id: notifId,
          title: 'Lembrete da NOVA',
          body: texto,
          when: when,
        );
      } catch (_) {
        // segue sem interromper UX
      }
    }
  }

  Future<void> _initTts() async {
    await _tts.awaitSpeakCompletion(true);
    await _selecionarEngineEVozMaisNatural();
    await _tts.setLanguage('pt-BR');
    await _tts.setSpeechRate(kIsWeb ? 0.52 : 0.50);
    await _tts.setPitch(1.0);
    await _tts.setVolume(1.0);
  }

  bool get _ttsEnabled => _config['voz_ativa'] == true;

  Future<void> _selecionarEngineEVozMaisNatural() async {
    try {
      final engines = await _tts.getEngines;
      if (engines is List && engines.isNotEmpty) {
        final lista = engines.map((e) => e.toString()).toList();
        String? escolhida;
        for (final engine in lista) {
          final l = engine.toLowerCase();
          if (l.contains('samsung') ||
              l.contains('vocalizer') ||
              l.contains('acapela')) {
            escolhida = engine;
            break;
          }
        }
        escolhida ??= lista.firstWhere(
          (e) => !e.toLowerCase().contains('google'),
          orElse: () => lista.first,
        );
        await _tts.setEngine(escolhida);
      }
    } catch (_) {
      // Alguns dispositivos não permitem trocar engine por app.
    }

    try {
      final voices = await _tts.getVoices;
      if (voices is! List) return;

      final preferidas = [
        'pt-br',
        'portuguese',
        'portugues',
        'natural',
        'online',
        'enhanced',
        'microsoft',
        'francisca',
        'helena',
        'maria',
        'luciana',
        'vitoria',
        'female',
        'woman',
        'feminina',
        'premium',
        'network',
        'neural',
        'wavenet',
      ];
      final evitar = ['male', 'masculina', 'masculino'];

      Map<dynamic, dynamic>? melhor;
      int melhorScore = -9999;

      for (final raw in voices) {
        if (raw is! Map) continue;
        final voice = raw.map(
          (key, value) => MapEntry(key.toString(), value?.toString() ?? ''),
        );
        final nome = (voice['name'] ?? '').toLowerCase();
        final locale =
            ((voice['locale'] ?? voice['language'] ?? '')).toLowerCase();
        final gender = (voice['gender'] ?? '').toLowerCase();

        if (!(locale.contains('pt-br') || locale.contains('pt_br'))) continue;

        int score = 0;
        if (locale.contains('pt-br') || locale.contains('pt_br')) score += 8;
        if (gender.contains('female') || gender.contains('femin')) score += 9;
        for (final item in preferidas) {
          if (nome.contains(item)) score += 5;
        }
        for (final item in evitar) {
          if (nome.contains(item)) score -= 12;
        }
        if (nome.contains('google')) score -= 8;

        if (score > melhorScore) {
          melhor = raw;
          melhorScore = score;
        }
      }

      if (melhor != null) {
        final nome = melhor['name']?.toString();
        final locale = (melhor['locale'] ?? melhor['language'])?.toString();
        if (nome != null && locale != null) {
          await _tts.setVoice({'name': nome, 'locale': locale});
        }
      }
    } catch (_) {
      // Mantém voz padrão quando API do dispositivo é limitada.
    }
  }

  String _textoMaisHumanoParaFala(String text) {
    var t = text.trim();
    if (t.isEmpty) return t;
    t = t.replaceAll(RegExp(r'https?://\S+'), ' ');
    t = t.replaceAll('\n', '. ');
    t = t.replaceAll(':', ', ');
    t = t.replaceAll(';', ', ');
    t = t.replaceAll(RegExp(r'[_*`#]'), ' ');
    t = t.replaceAll('%', ' por cento');
    t = t.replaceAll('N.O.V.A', 'NOVA');
    t = t.replaceAll(RegExp(r'\s+'), ' ').trim();
    return t;
  }

  List<String> _quebrarEmBlocosDeFala(String text, {int maxChars = 420}) {
    if (text.length <= maxChars) return [text];
    final partes = text.split(RegExp(r'(?<=[.!?])\s+'));
    final blocos = <String>[];
    var buffer = '';
    for (final p in partes) {
      final item = p.trim();
      if (item.isEmpty) continue;
      if ((buffer.length + item.length + 1) <= maxChars) {
        buffer = buffer.isEmpty ? item : '$buffer $item';
      } else {
        if (buffer.isNotEmpty) blocos.add(buffer);
        buffer = item;
      }
    }
    if (buffer.isNotEmpty) blocos.add(buffer);
    return blocos.isEmpty ? [text] : blocos;
  }

  bool get _neuralVoiceHybridEnabled => _config['voice_neural_hybrid'] != false;

  Future<bool> _speakNeuralOnline(String text, int requestId) async {
    final profile =
        (_config['voice_profile']?.toString().trim().toLowerCase() ??
                'feminina')
            .replaceAll(' ', '');
    final payload = await _api.synthesizeNeuralVoice(
      text,
      voiceProfile: profile.isEmpty ? 'feminina' : profile,
    );
    final b64 = payload['audio_base64']?.toString() ?? '';
    if (b64.isEmpty) return false;
    Uint8List bytes;
    try {
      bytes = base64Decode(b64);
    } catch (_) {
      return false;
    }
    if (bytes.isEmpty) return false;
    if (requestId != _speakRequestId) return false;
    await _voicePlayer.stop();
    if (requestId != _speakRequestId) return false;
    await _voicePlayer.play(BytesSource(bytes));
    return true;
  }

  Future<void> _speak(String text) async {
    if (!_ttsEnabled) return;
    final requestId = ++_speakRequestId;
    final clean = _textoMaisHumanoParaFala(text);
    if (clean.isEmpty) return;
    final textoVoz =
        clean.length > 900 ? '${clean.substring(0, 900)}...' : clean;
    await _voicePlayer.stop();
    await _tts.stop();

    if (_neuralVoiceHybridEnabled) {
      try {
        final ok = await _speakNeuralOnline(textoVoz, requestId);
        if (ok) {
          if (mounted) {
            setState(() {
              _systemStatus = 'Voz neural online ativa.';
            });
          }
          return;
        }
      } catch (_) {
        if (mounted) {
          setState(() {
            _systemStatus = 'Voz neural indisponível, usando voz local.';
          });
        }
      }
    }

    if (requestId != _speakRequestId) return;
    if (mounted) {
      setState(() {
        _systemStatus = 'Usando voz local do dispositivo.';
      });
    }
    final blocos = _quebrarEmBlocosDeFala(textoVoz);
    for (final bloco in blocos) {
      if (requestId != _speakRequestId) break;
      await _tts.speak(bloco);
      await Future<void>.delayed(const Duration(milliseconds: 20));
    }
  }

  Future<void> _initSpeech() async {
    if (!_listenModeEnabled) {
      if (!mounted) return;
      setState(() {
        _speechReady = false;
        _isListening = false;
        _systemStatus = 'Modo escuta desativado.';
      });
      return;
    }

    final available = await _speech.initialize(
      onStatus: (status) {
        if (!mounted) return;
        if (status == 'done' || status == 'notListening') {
          setState(() => _isListening = false);
          if (_listenModeEnabled &&
              _effectiveContinuousWake &&
              !_manualListeningStop) {
            Future<void>.delayed(const Duration(milliseconds: 250), () {
              if (!mounted || _isListening || !_speechReady) return;
              _startListening();
            });
          }
        }
      },
      onError: (_) {
        if (!mounted) return;
        setState(() {
          _isListening = false;
          _systemStatus = 'Falha no microfone.';
        });
      },
    );

    if (!mounted) return;
    setState(() {
      _speechReady = available;
      _systemStatus = available ? 'Tudo pronto.' : 'Microfone indisponível.';
    });
    if (available && _listenModeEnabled && _effectiveContinuousWake) {
      _startListening();
    }
  }

  Future<void> _finalizarEscutaEProcessarVoz(String words) async {
    _manualListeningStop = true;
    try {
      await _speech.stop();
    } catch (_) {
      // Falha de parada não deve bloquear o envio por voz.
    }
    if (!mounted) return;
    setState(() {
      _isListening = false;
      _systemStatus = 'Comando de voz capturado.';
    });
    await _handleWakeWordVoice(words);
  }

  Future<void> _startListening() async {
    if (!_listenModeEnabled) {
      if (!mounted) return;
      setState(() {
        _isListening = false;
        _systemStatus = 'Modo escuta desativado.';
      });
      return;
    }
    if (!_speechReady) return;
    _manualListeningStop = false;
    if (!mounted) return;
    setState(() {
      _isListening = true;
      _executedFromVoice = false;
      _systemStatus = 'Estou ouvindo você...';
    });

    await _speech.listen(
      localeId: 'pt_BR',
      listenOptions: SpeechListenOptions(
        partialResults: true,
        cancelOnError: true,
        listenMode: ListenMode.dictation,
      ),
      listenFor: const Duration(seconds: 20),
      pauseFor: const Duration(seconds: 4),
      onResult: (result) {
        if (!mounted) return;
        final words = result.recognizedWords.trim();
        _messageController.text = words;
        _messageController.selection = TextSelection.fromPosition(
          TextPosition(offset: _messageController.text.length),
        );

        if (result.finalResult && words.isNotEmpty && !_executedFromVoice) {
          _executedFromVoice = true;
          _finalizarEscutaEProcessarVoz(words);
        }
      },
    );
  }

  Future<void> _toggleListening() async {
    if (!_listenModeEnabled) {
      if (!mounted) return;
      setState(() => _systemStatus = 'Ative o modo escuta nas configurações.');
      return;
    }
    if (!_speechReady) {
      await _initSpeech();
      if (!_speechReady) return;
    }

    if (_isListening) {
      _manualListeningStop = true;
      await _speech.stop();
      if (!mounted) return;
      setState(() {
        _isListening = false;
        _systemStatus = 'Escuta pausada.';
      });
      return;
    }

    await _startListening();
  }

  Future<void> _handleWakeWordVoice(String words) async {
    final wakeWord =
        (_config['wake_word']?.toString().trim().toLowerCase() ?? 'nova');
    if (wakeWord.isEmpty) return;

    final cleaned = words.trim();
    if (cleaned.isEmpty) return;

    final lower = _normalizarParaMatch(cleaned);
    final wake = _normalizarParaMatch(wakeWord);
    final temWake = RegExp(r'\b' + RegExp.escape(wake) + r'\b').hasMatch(lower);

    if (!temWake) {
      // Quando o usuário toca no microfone manualmente, aceita frases naturais longas sem wake word.
      if (lower.split(' ').length >= 4) {
        final comandoSemWake = _limparComandoDeVoz(cleaned);
        await _executeCommand(comandoSemWake, fromVoice: true);
        return;
      }
      if (!mounted) return;
      setState(() {
        _systemStatus =
            'Diga "$wakeWord" para ativar, ou fale um comando completo.';
      });
      return;
    }

    final command = _extrairComandoAposWakeWord(cleaned, wakeWord);

    if (command.isEmpty) {
      const ack = 'Oi chefe.';
      if (!mounted) return;
      setState(() {
        _chat.add(const NovaChatLine(fromUser: false, text: ack));
        _systemStatus = 'Wake word detectada.';
      });
      await _speak(ack);
      return;
    }

    await _executeCommand(_limparComandoDeVoz(command), fromVoice: true);
  }

  String _normalizarParaMatch(String input) {
    var t = input.toLowerCase();
    const mapa = {
      'á': 'a',
      'à': 'a',
      'â': 'a',
      'ã': 'a',
      'é': 'e',
      'ê': 'e',
      'í': 'i',
      'ó': 'o',
      'ô': 'o',
      'õ': 'o',
      'ú': 'u',
      'ç': 'c',
    };
    mapa.forEach((k, v) => t = t.replaceAll(k, v));
    t = t.replaceAll(RegExp(r'[^\w\s]'), ' ');
    t = t.replaceAll(RegExp(r'\s+'), ' ').trim();
    return t;
  }

  String _extrairComandoAposWakeWord(String frase, String wakeWord) {
    final pattern = RegExp(
      r'(?:^|\s)(?:ei|hey|ok|okay|ola|olá)?\s*' +
          RegExp.escape(wakeWord) +
          r'[:,]?\s*',
      caseSensitive: false,
    );
    return frase.replaceFirst(pattern, '').trim();
  }

  String _limparComandoDeVoz(String comando) {
    var t = comando.trim();
    t = t.replaceFirst(
      RegExp(
        r'^(por favor|por gentileza|pode|você pode|voce pode|consegue|quero que você|quero que voce)\s+',
        caseSensitive: false,
      ),
      '',
    );
    t = t.replaceFirst(
      RegExp(r'^(pra mim|para mim)\s+', caseSensitive: false),
      '',
    );
    t = t.replaceAll(RegExp(r'\s+'), ' ').trim();
    return t;
  }

  Future<void> _handleSendMessage() async {
    final message = _messageController.text.trim();
    final attached = _composerAttachmentName;
    if (message.isEmpty && attached == null) return;
    final outbound = attached == null
        ? message
        : message.isEmpty
            ? 'Arquivo anexado: $attached'
            : '$message\n\n[Arquivo anexado: $attached]';
    await _executeCommand(outbound, fromVoice: false);
    if (!mounted) return;
    setState(() {
      _composerAttachmentName = null;
    });
  }

  Future<void> _pickComposerAttachment() async {
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: false,
      type: FileType.any,
    );
    if (result == null || result.files.isEmpty) return;
    final file = result.files.first;
    if (!mounted) return;
    setState(() {
      _composerAttachmentName = file.name;
    });
    _showSnack('Arquivo anexado: ${file.name}');
  }

  Future<void> _pickQuickPhoto() async {
    try {
      final picked = await _imagePicker.pickImage(
        source: ImageSource.camera,
        preferredCameraDevice: CameraDevice.rear,
        imageQuality: 90,
      );
      if (picked == null) return;
      if (!mounted) return;
      setState(() {
        _composerAttachmentName = picked.name;
      });
      _showSnack('Foto capturada: ${picked.name}');
    } catch (_) {
      final result = await FilePicker.platform.pickFiles(
        allowMultiple: false,
        type: FileType.image,
      );
      if (result == null || result.files.isEmpty) {
        _showSnack('Não consegui abrir a câmera agora.');
        return;
      }
      final file = result.files.first;
      if (!mounted) return;
      setState(() {
        _composerAttachmentName = file.name;
      });
      _showSnack('Imagem adicionada: ${file.name}');
    }
  }

  bool _isMusicCommand(String input) {
    final t = input.toLowerCase().trim();
    return t.contains('tocar musica') ||
        t.contains('tocar música') ||
        t.contains('abrir musica') ||
        t.contains('abrir música') ||
        t == '/musica' ||
        t == '/música' ||
        t == '/play';
  }

  bool _isPlaylistFavoritaCommand(String input) {
    final t = _normalizarParaMatch(input);
    return t.contains('playlist favorita') ||
        t.contains('play list favorita') ||
        t.contains('tocar a playlist favorita') ||
        t.contains('toque minha playlist favorita') ||
        t.contains('toque a playlist favorita dela');
  }

  bool _isYoutubeOpenCommand(String input) {
    final t = _normalizarParaMatch(input);
    return t == 'abrir youtube' ||
        t == 'abre youtube' ||
        t == 'open youtube' ||
        t == 'abrir o youtube';
  }

  bool _isMapsOpenCommand(String input) {
    final t = _normalizarParaMatch(input);
    return t == 'abrir maps' ||
        t == 'abre maps' ||
        t == 'open maps' ||
        t == 'abrir o maps' ||
        t == 'abrir mapa' ||
        t == 'abrir mapas' ||
        t == 'abrir google maps' ||
        t == 'abre google maps';
  }

  String? _extractYoutubeSearchQuery(String input) {
    final cleaned = input.trim();
    if (cleaned.isEmpty) return null;

    final patterns = <RegExp>[
      RegExp(
        r'^(?:pesquise|pesquisar|procure|procurar|busque|buscar)\s+(?:no\s+)?youtube\s+(?:por|sobre)?\s*(.+)$',
        caseSensitive: false,
      ),
      RegExp(
        r'^(?:abra|abrir|abre|open)\s+(?:o\s+)?youtube\s+(?:e\s+)?(?:pesquise|pesquisar|procure|procurar|busque|buscar)?\s*(?:por|sobre)?\s*(.+)$',
        caseSensitive: false,
      ),
      RegExp(
        r'^(?:youtube)\s+(?:pesquise|pesquisar|procure|procurar|busque|buscar)?\s*(?:por|sobre)?\s*(.+)$',
        caseSensitive: false,
      ),
    ];

    for (final pattern in patterns) {
      final match = pattern.firstMatch(cleaned);
      if (match == null) continue;
      final query = (match.group(1) ?? '').trim();
      if (query.isEmpty) continue;
      return query.trim().replaceAll(RegExp(r'^[,:-]+|[,:-]+$'), '').trim();
    }

    return null;
  }

  String? _extractMapsSearchQuery(String input) {
    final cleaned = input.trim();
    if (cleaned.isEmpty) return null;

    final patterns = <RegExp>[
      RegExp(
        r'^(?:pesquise|pesquisar|procure|procurar|busque|buscar)\s+(?:no\s+)?(?:google\s+)?maps?\s+(?:por|sobre|em)?\s*(.+)$',
        caseSensitive: false,
      ),
      RegExp(
        r'^(?:abra|abrir|abre|open)\s+(?:o\s+)?(?:google\s+)?maps?\s+(?:e\s+)?(?:pesquise|pesquisar|procure|procurar|busque|buscar)?\s*(?:por|sobre|em)?\s*(.+)$',
        caseSensitive: false,
      ),
      RegExp(
        r'^(?:mapa|mapas|maps|google maps)\s+(?:pesquise|pesquisar|procure|procurar|busque|buscar)?\s*(?:por|sobre|em)?\s*(.+)$',
        caseSensitive: false,
      ),
    ];

    for (final pattern in patterns) {
      final match = pattern.firstMatch(cleaned);
      if (match == null) continue;
      final query = (match.group(1) ?? '').trim();
      if (query.isEmpty) continue;
      return query.trim().replaceAll(RegExp(r'^[,:-]+|[,:-]+$'), '').trim();
    }

    return null;
  }

  Future<String> _abrirYoutube([String query = '']) async {
    final normalizedQuery = query.trim();
    final uri = normalizedQuery.isEmpty
        ? Uri.parse('https://www.youtube.com')
        : Uri.https('www.youtube.com', '/results', {
            'search_query': normalizedQuery,
          });
    final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!ok) {
      return normalizedQuery.isEmpty
          ? 'Não consegui abrir o YouTube agora.'
          : 'Não consegui abrir a pesquisa no YouTube agora.';
    }
    return normalizedQuery.isEmpty
        ? 'Abrindo o YouTube.'
        : 'Abrindo pesquisa no YouTube por "$normalizedQuery".';
  }

  Future<String> _abrirMaps([String query = '']) async {
    final normalizedQuery = query.trim();
    final uri = normalizedQuery.isEmpty
        ? Uri.parse('https://www.google.com/maps')
        : Uri.parse(
            'https://www.google.com/maps/search/?api=1&query=${Uri.encodeComponent(normalizedQuery)}',
          );
    final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!ok) {
      return normalizedQuery.isEmpty
          ? 'Não consegui abrir o Maps agora.'
          : 'Não consegui abrir a busca no Maps agora.';
    }
    return normalizedQuery.isEmpty
        ? 'Abrindo o Maps.'
        : 'Abrindo busca no Maps por "$normalizedQuery".';
  }

  Future<String> _abrirPlaylistFavoritaYoutube() async {
    const url =
        'https://youtube.com/playlist?list=PLR5Cmjo90BNguiSb2wDShPdKoa-Xiw5x1&si=ZsqnYwcp7fkvUj35';
    final uri = Uri.parse(url);
    final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (ok) {
      return 'Abrindo sua playlist favorita no YouTube, chefe.';
    }
    return 'Não consegui abrir o YouTube agora.';
  }

  Future<String> _adicionarMusicasNaBiblioteca() async {
    if (!PlatformCapabilities.supportsLocalMusicLibrary) {
      return 'Biblioteca local de músicas não está disponível nesta plataforma.';
    }

    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac'],
      allowMultiple: true,
    );
    if (result == null || result.files.isEmpty) {
      return 'Nenhum arquivo de música foi selecionado.';
    }

    final files = <Map<String, String>>[];
    for (final file in result.files) {
      final path = file.path ?? '';
      if (path.isEmpty) continue;
      files.add({'path': path, 'name': file.name});
    }
    if (files.isEmpty) return 'Arquivos inválidos.';

    await _localDb.addMusicFiles(files);
    await _loadMusicLibrary();
    return '${files.length} música(s) adicionada(s) à biblioteca local.';
  }

  Future<String> _tocarMusicaLocal([String query = '']) async {
    if (!PlatformCapabilities.supportsLocalMusicLibrary) {
      return 'A reprodução local de músicas só está disponível fora da Web.';
    }

    if (_musicLibrary.isEmpty) {
      final added = await _adicionarMusicasNaBiblioteca();
      if (_musicLibrary.isEmpty) return added;
    }

    Map<String, String>? selecionada;
    final q = query.toLowerCase().trim();
    if (q.isNotEmpty) {
      for (final item in _musicLibrary) {
        final nome = (item['name'] ?? '').toLowerCase();
        if (nome.contains(q)) {
          selecionada = item;
          break;
        }
      }
    }
    selecionada ??= _musicLibrary.first;

    final path = selecionada['path'] ?? '';
    if (path.isEmpty) return 'Arquivo de música inválido.';

    await _audioPlayer.stop();
    await _audioPlayer.play(DeviceFileSource(path));
    return 'Tocando agora: ${selecionada['name']}';
  }

  String _listarMusicas() {
    if (!PlatformCapabilities.supportsLocalMusicLibrary) {
      return 'A biblioteca local de músicas não está disponível nesta plataforma.';
    }
    if (_musicLibrary.isEmpty) return 'Sua biblioteca de músicas está vazia.';
    final itens = _musicLibrary.take(20).toList();
    final linhas = <String>[];
    for (var i = 0; i < itens.length; i++) {
      linhas.add('${i + 1}. ${itens[i]['name']}');
    }
    return 'Biblioteca local:\n${linhas.join('\n')}';
  }

  Future<String?> _handleLocalUiCommands(String message) async {
    final t = _normalizarParaMatch(message);

    if (t == 'abrir usuarios' || t == 'open usuarios') {
      _openUsersDialog();
      return 'Abrindo usuários.';
    }
    if (t == 'abrir ensinar' || t == 'abrir ensino') {
      _openTeachDialog();
      return 'Abrindo tela de ensino.';
    }
    if (t == 'abrir editar base' || t == 'abrir base de conhecimento') {
      _openKnowledgeDialog();
      return 'Abrindo base de conhecimento.';
    }
    if (t == 'abrir configuracoes' || t == 'abrir config') {
      _openConfigDialog();
      return 'Abrindo configurações.';
    }
    if (t == 'abrir lembretes' || t == 'mostrar lembretes') {
      _openRemindersDialog();
      return 'Abrindo lembretes.';
    }
    if (t == 'abrir documentos' ||
        t == 'analisar documento' ||
        t == '/documentos') {
      _openDocumentAnalysisDialog();
      return 'Abrindo análise de documentos.';
    }
    if (t == 'abrir help' ||
        t == 'abrir ajuda' ||
        t == 'mostrar comandos' ||
        t == '/help') {
      _openHelpDialog();
      return 'Abrindo central de ajuda.';
    }
    if (t == 'abrir compatibilidade' ||
        t == 'mostrar compatibilidade' ||
        t == '/compatibilidade') {
      _openCompatibilityDialog();
      return 'Abrindo compatibilidade do dispositivo.';
    }
    if (t == 'ativar modo escuta' ||
        t == 'ligar modo escuta' ||
        t == 'ativar escuta') {
      setState(() => _config['escuta_ativa'] = true);
      await _saveLocalState();
      await _initSpeech();
      return 'Modo escuta ativado.';
    }
    if (t == 'desativar modo escuta' ||
        t == 'desligar modo escuta' ||
        t == 'desativar escuta') {
      setState(() => _config['escuta_ativa'] = false);
      _manualListeningStop = true;
      await _speech.stop();
      await BackgroundWakeService.stop();
      await _saveLocalState();
      if (mounted) {
        setState(() => _isListening = false);
      }
      return 'Modo escuta desativado.';
    }
    if (t.contains('adicionar musica') || t.contains('adicionar musicas')) {
      return _adicionarMusicasNaBiblioteca();
    }
    if (t.contains('abrir bluetooth') ||
        t.contains('conectar bluetooth') ||
        t.contains('parear bluetooth') ||
        t.contains('conectar dispositivo bluetooth')) {
      final ok = await _deviceConnectivity.openBluetoothSettings();
      return ok
          ? 'Abrindo Bluetooth para conectar seu dispositivo.'
          : 'Este atalho de Bluetooth funciona no Android.';
    }
    if (t.contains('conectar tv') ||
        t.contains('conectar na tv') ||
        t.contains('espelhar tela') ||
        t.contains('transmitir tela') ||
        t.contains('abrir cast')) {
      final ok = await _deviceConnectivity.openCastSettings();
      return ok
          ? 'Abrindo configurações de transmissão de tela para TV/telas.'
          : 'Este atalho de transmissão funciona no Android.';
    }
    if (t.contains('android auto') ||
        t.contains('abrir auto') ||
        t.contains('conectar carro')) {
      final ok = await _deviceConnectivity.openAndroidAuto();
      return ok
          ? 'Abrindo Android Auto.'
          : 'Não consegui abrir Android Auto agora.';
    }
    if (t.contains('abrir termux') ||
        t.contains('modo termux') ||
        t.contains('terminal seguro')) {
      final ok = await _deviceConnectivity.openTermux();
      return ok
          ? 'Abrindo Termux em modo de segurança defensiva.'
          : 'Não consegui abrir o Termux agora.';
    }
    final mapsQuery = _extractMapsSearchQuery(message);
    if (mapsQuery != null) {
      return _abrirMaps(mapsQuery);
    }
    if (_isMapsOpenCommand(message)) {
      return _abrirMaps();
    }
    final youtubeQuery = _extractYoutubeSearchQuery(message);
    if (youtubeQuery != null) {
      return _abrirYoutube(youtubeQuery);
    }
    if (_isYoutubeOpenCommand(message)) {
      return _abrirYoutube();
    }
    if (_isPlaylistFavoritaCommand(message)) {
      return _abrirPlaylistFavoritaYoutube();
    }
    if (t == '/varredura' ||
        t == '/scan' ||
        t.contains('varredura do sistema') ||
        t.contains('status detalhado do sistema') ||
        t.contains('status de software e hardware') ||
        t.contains('varredura de software e hardware')) {
      return _gerarVarreduraSoftwareHardware();
    }
    if (t == '/seguranca' ||
        t == '/segurança' ||
        t == '/auditoria' ||
        t.contains('varredura de seguranca') ||
        t.contains('varredura de segurança') ||
        t.contains('auditoria de seguranca') ||
        t.contains('auditoria de segurança')) {
      return _gerarVarreduraSegurancaFormal();
    }
    if (t.contains('listar musicas') || t == '/musicas') {
      return _listarMusicas();
    }
    if (t.contains('parar musica') || t == '/stop') {
      await _audioPlayer.stop();
      return 'Música parada.';
    }
    if (_isMusicCommand(message)) {
      final q = message
          .toLowerCase()
          .replaceAll('tocar música', '')
          .replaceAll('tocar musica', '')
          .replaceAll('/play', '')
          .trim();
      return _tocarMusicaLocal(q);
    }

    return null;
  }

  Future<String> _gerarVarreduraSoftwareHardware() async {
    final hasPin = await _secureSecrets.hasAdminPin();
    final canBio = await _appSecurity.canUseBiometrics();
    return _systemScan.buildDetailedReport(
      api: _api,
      config: _config,
      hasAdminPin: hasPin,
      canUseBiometric: canBio,
    );
  }

  Future<String> _gerarVarreduraSegurancaFormal() async {
    final localReport = await _gerarVarreduraSoftwareHardware();
    try {
      final audit = await _api.getSecurityAudit();
      final score = audit['score']?.toString() ?? '-';
      final nivel = audit['nivel']?.toString() ?? '-';
      final achados =
          (audit['achados'] is List) ? (audit['achados'] as List) : const [];
      final prioridades = (audit['prioridades'] is List)
          ? (audit['prioridades'] as List)
          : const [];

      final linhas = <String>[
        'Checklist formal de segurança:',
        '- Score: $score/100 ($nivel)',
        '- Achados relevantes:',
      ];
      if (achados.isEmpty) {
        linhas.add('  * Nenhum achado crítico retornado pelo backend.');
      } else {
        for (final item in achados.take(6)) {
          if (item is! Map) continue;
          final sev = item['severidade']?.toString() ?? 'info';
          final titulo = item['titulo']?.toString() ?? 'achado';
          final acao = item['acao']?.toString() ?? 'revisar';
          linhas.add('  * [$sev] $titulo -> $acao');
        }
      }
      linhas.add('- Hardening por prioridade:');
      if (prioridades.isEmpty) {
        linhas
            .add('  * Revisar segredos, permissões, autenticação e auditoria.');
      } else {
        for (final p in prioridades.take(6)) {
          linhas.add('  * ${p.toString()}');
        }
      }

      linhas.add('');
      linhas.add(localReport);
      return linhas.join('\n');
    } catch (_) {
      return 'Não consegui consultar a auditoria formal no backend agora.\n\n$localReport';
    }
  }

  Future<String?> _promptAdminPin() async {
    if (!mounted) return null;
    final controller = TextEditingController();
    String? pin;
    await showDialog<void>(
      context: context,
      builder: (context) {
        return AlertDialog(
          backgroundColor: const Color(0xFF04192A),
          title: const Text(
            'PIN Administrativo',
            style: TextStyle(color: Color(0xFFD4F4FF)),
          ),
          content: TextField(
            controller: controller,
            autofocus: true,
            obscureText: true,
            keyboardType: TextInputType.number,
            style: const TextStyle(color: Color(0xFFD4F4FF)),
            decoration: const InputDecoration(
              hintText: 'Digite o PIN',
              hintStyle: TextStyle(color: Color(0xFF6E8DA5)),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancelar'),
            ),
            FilledButton(
              onPressed: () {
                pin = controller.text.trim();
                Navigator.of(context).pop();
              },
              child: const Text('Confirmar'),
            ),
          ],
        );
      },
    );
    controller.dispose();
    return pin;
  }

  Future<bool> _ensureAdminAccess() async {
    if (_config['admin_guard'] == false) return true;

    final now = DateTime.now();
    if (_adminUnlocked &&
        _adminUnlockedAt != null &&
        now.difference(_adminUnlockedAt!) < const Duration(minutes: 10)) {
      return true;
    }

    final canBio = await _appSecurity.canUseBiometrics();
    if (canBio) {
      final ok = await _appSecurity.authenticateAdmin();
      if (ok) {
        _adminUnlocked = true;
        _adminUnlockedAt = DateTime.now();
        return true;
      }
    }

    final hasPin = await _secureSecrets.hasAdminPin();
    if (!hasPin) return false;

    final pin = await _promptAdminPin();
    if (pin == null || pin.isEmpty) return false;

    final ok = await _secureSecrets.validateAdminPin(pin);
    if (!ok) {
      _showSnack('PIN inválido.');
      return false;
    }
    _adminUnlocked = true;
    _adminUnlockedAt = DateTime.now();
    return true;
  }

  Future<void> _openRemindersDialog() async {
    final textController = TextEditingController();
    DateTime? selectedDateTime;

    await _loadReminders();
    if (!mounted) return;

    await showDialog<void>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setLocalState) {
            Future<void> addReminder() async {
              final text = textController.text.trim();
              if (text.isEmpty) return;
              if (selectedDateTime == null) {
                _showSnack('Defina data e hora para o lembrete.');
                return;
              }
              final whenIso = selectedDateTime?.toIso8601String() ?? '';
              try {
                Map<String, dynamic>? createdItem;
                bool synced = false;
                try {
                  final created =
                      await _api.addReminder(text: text, when: whenIso);
                  if (created['ok'] == true && created['item'] is Map) {
                    createdItem =
                        Map<String, dynamic>.from(created['item'] as Map);
                    synced = true;
                  }
                } catch (_) {
                  // fallback local logo abaixo
                }

                createdItem ??= {
                  'id': 'local_${DateTime.now().millisecondsSinceEpoch}',
                  'texto': text,
                  'quando': whenIso,
                  'criado_em': DateTime.now().toIso8601String(),
                  'feito': false,
                };

                bool localSaved = false;
                try {
                  await _localDb.upsertReminder(createdItem);
                  localSaved = true;
                } catch (_) {
                  localSaved = false;
                }
                if (!synced && !localSaved) {
                  throw Exception('local_reminder_save_failed');
                }
                final notifId = _notificationIdFromReminderId(
                  (createdItem['id'] ?? '').toString(),
                );
                await _notifications.scheduleReminder(
                  id: notifId,
                  title: 'Lembrete da NOVA',
                  body: text,
                  when: selectedDateTime!,
                );
                textController.clear();
                selectedDateTime = null;
                await _loadReminders();
                setLocalState(() {});
                _showSnack(
                  synced
                      ? 'Lembrete salvo e sincronizado com backend.'
                      : 'Lembrete salvo localmente (sem backend no momento).',
                );
              } catch (_) {
                _showSnack('Falha ao salvar lembrete.');
              }
            }

            Future<void> pickDateTime() async {
              final date = await showDatePicker(
                context: context,
                firstDate: DateTime.now(),
                lastDate: DateTime.now().add(const Duration(days: 3650)),
                initialDate: DateTime.now(),
              );
              if (date == null || !context.mounted) return;
              final time = await showTimePicker(
                context: context,
                initialTime: TimeOfDay.now(),
              );
              if (time == null) return;
              selectedDateTime = DateTime(
                date.year,
                date.month,
                date.day,
                time.hour,
                time.minute,
              );
              setLocalState(() {});
            }

            return NovaPanelDialog(
              title: 'LEMBRETES',
              child: SizedBox(
                width: 640,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    NovaInput(
                        controller: textController,
                        hintText: 'Ex: lembrar de pagar conta'),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            selectedDateTime == null
                                ? 'Sem horário definido'
                                : 'Alerta: ${selectedDateTime!.toLocal()}',
                            style: const TextStyle(color: Color(0xFF6FA6C6)),
                          ),
                        ),
                        TextButton(
                          onPressed: pickDateTime,
                          child: const Text('Definir horário'),
                        ),
                        const SizedBox(width: 8),
                        FilledButton(
                          onPressed: addReminder,
                          child: const Text('Salvar'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxHeight: 320),
                      child: _reminders.isEmpty
                          ? const Center(
                              child: Padding(
                                padding: EdgeInsets.all(8),
                                child: Text(
                                  'Nenhum lembrete salvo.',
                                  style: TextStyle(color: Color(0xFF5E86A3)),
                                ),
                              ),
                            )
                          : ListView.separated(
                              itemCount: _reminders.length,
                              separatorBuilder: (_, __) =>
                                  const SizedBox(height: 8),
                              itemBuilder: (context, index) {
                                final item = _reminders[index];
                                final txt = item['texto']?.toString() ?? '-';
                                final when = item['quando']?.toString() ?? '';
                                return Container(
                                  padding: const EdgeInsets.all(10),
                                  decoration: BoxDecoration(
                                    borderRadius: BorderRadius.circular(10),
                                    color: const Color(0x52021322),
                                    border: Border.all(
                                        color: const Color(0xFF084D74)),
                                  ),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        txt,
                                        style: const TextStyle(
                                          color: Color(0xFFD9F5FF),
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        when.isEmpty ? 'Sem horário' : when,
                                        style: const TextStyle(
                                          color: Color(0xFF6DA7C8),
                                          fontSize: 12,
                                        ),
                                      ),
                                    ],
                                  ),
                                );
                              },
                            ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );

    textController.dispose();
  }

  Future<void> _openCompatibilityDialog() async {
    if (!mounted) return;
    final itens = PlatformCapabilities.matrixRich();
    await showDialog<void>(
      context: context,
      builder: (context) {
        return NovaPanelDialog(
          title: 'COMPATIBILIDADE',
          child: SizedBox(
            width: 620,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Dispositivo atual: ${PlatformCapabilities.platformName}',
                  style: const TextStyle(
                    color: Color(0xFFBDE8FF),
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 12),
                ...itens.map(
                  (item) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: const Color(0x55021425),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: const Color(0xFF0A4E75)),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  item['label'] ?? '-',
                                  style: const TextStyle(
                                    color: Color(0xFFD6F4FF),
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  item['detail'] ?? '',
                                  style: const TextStyle(
                                    color: Color(0xFF76A6C2),
                                    fontSize: 12,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 10),
                          NovaCapabilityBadge(
                              status: item['status'] ?? 'parcial'),
                        ],
                      ),
                    ),
                  ),
                ),
                const Text(
                  'Dica: no Android, a NOVA suporta wake word em segundo plano.',
                  style: TextStyle(
                    color: Color(0xFF6E9AB8),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _openDocumentAnalysisDialog() async {
    final allowed = await _ensureAdminAccess();
    if (!mounted) return;
    if (!allowed) {
      _showSnack('Acesso administrativo negado.');
      return;
    }

    String selectedName = '';
    Uint8List? selectedBytes;
    bool loading = false;
    String error = '';
    String reportText = '';
    String learningText = '';
    String subjectsText = '';

    String formatarRelatorio(Map<String, dynamic> payload) {
      final report = (payload['report'] is Map)
          ? Map<String, dynamic>.from(payload['report'] as Map)
          : <String, dynamic>{};
      final stats = (report['stats'] is Map)
          ? Map<String, dynamic>.from(report['stats'] as Map)
          : <String, dynamic>{};
      final keywords = (report['keywords'] is List)
          ? (report['keywords'] as List)
          : const [];
      final risks =
          (report['risks'] is List) ? (report['risks'] as List) : const [];
      final excerpts = (report['sample_excerpts'] is List)
          ? (report['sample_excerpts'] as List)
          : const [];
      final recs = (report['recommendations'] is List)
          ? (report['recommendations'] as List)
          : const [];

      final lines = <String>[
        'Relatório de documento',
        '- Arquivo: ${report['file_name'] ?? '-'}',
        '- Gerado em: ${report['generated_at'] ?? '-'}',
        '- Tamanho: ${stats['bytes'] ?? 0} bytes',
        '- Caracteres: ${stats['chars'] ?? 0}',
        '- Palavras: ${stats['words'] ?? 0}',
        '- Páginas estimadas: ${stats['estimated_pages'] ?? 0}',
        '',
        'Resumo executivo:',
        '${report['executive_summary'] ?? 'Sem resumo.'}',
        '',
        'Palavras-chave:',
      ];
      if (keywords.isEmpty) {
        lines.add('- nenhuma');
      } else {
        for (final k in keywords.take(12)) {
          if (k is! Map) continue;
          lines.add('- ${k['token']}: ${k['count']}');
        }
      }
      lines.add('');
      lines.add('Riscos detectados:');
      if (risks.isEmpty) {
        lines.add('- nenhum risco explícito encontrado');
      } else {
        for (final r in risks.take(8)) {
          lines.add('- ${r.toString()}');
        }
      }
      lines.add('');
      lines.add('Trechos relevantes:');
      if (excerpts.isEmpty) {
        lines.add('- sem trechos');
      } else {
        for (final e in excerpts.take(4)) {
          lines.add('- ${e.toString()}');
        }
      }
      lines.add('');
      lines.add('Recomendações:');
      for (final r in recs.take(6)) {
        lines.add('- ${r.toString()}');
      }
      return lines.join('\n');
    }

    Future<void> analisarSelecionado(StateSetter setLocalState) async {
      if (selectedBytes == null || selectedName.isEmpty) {
        setLocalState(() => error = 'Selecione um arquivo antes.');
        return;
      }
      setLocalState(() {
        loading = true;
        error = '';
      });
      try {
        final out = await _api.analyzeDocument(
          fileName: selectedName,
          bytes: selectedBytes!,
        );
        final txt = formatarRelatorio(out);
        final learning = (out['learning'] is Map)
            ? Map<String, dynamic>.from(out['learning'] as Map)
            : <String, dynamic>{};
        final learnOk = learning['ok'] == true;
        final localFallback = learning['local_fallback'] == true;
        final learnMsg = learnOk
            ? 'Aprendizado automático: OK • base atualizada.'
            : localFallback
                ? 'Relatório gerado localmente. O backend não possui endpoint de análise.'
                : (learning['skipped'] == true
                    ? 'Aprendizado automático desativado.'
                    : 'Aprendizado automático: sem atualização.');
        setLocalState(() {
          reportText = txt;
          learningText = learnMsg;
          final sm = (learning['subject_memory'] is Map)
              ? Map<String, dynamic>.from(learning['subject_memory'] as Map)
              : <String, dynamic>{};
          final subs =
              (sm['subjects'] is List) ? (sm['subjects'] as List) : const [];
          if (subs.isNotEmpty) {
            subjectsText =
                'Assuntos aprendidos: ${subs.map((e) => e.toString()).join(", ")}';
          } else {
            subjectsText = 'Assuntos aprendidos: nenhum identificado.';
          }
        });
      } catch (e) {
        setLocalState(() {
          error = _humanizeApiError(
            e,
            fallback: 'Falha ao analisar documento.',
          );
        });
      } finally {
        if (context.mounted) setLocalState(() => loading = false);
      }
    }

    Future<void> selecionarArquivo(StateSetter setLocalState) async {
      final res = await FilePicker.platform.pickFiles(
        allowMultiple: false,
        withData: true,
        type: FileType.custom,
        allowedExtensions: ['txt', 'md', 'pdf', 'docx', 'json', 'csv', 'log'],
      );
      if (res == null || res.files.isEmpty) return;
      final f = res.files.first;
      Uint8List? bytes = f.bytes;
      if (bytes == null && (f.path ?? '').isNotEmpty && !kIsWeb) {
        try {
          bytes = await File(f.path!).readAsBytes();
        } catch (_) {
          bytes = null;
        }
      }
      if (bytes == null || bytes.isEmpty) {
        setLocalState(() => error = 'Não consegui ler o arquivo selecionado.');
        return;
      }
      setLocalState(() {
        selectedName = f.name;
        selectedBytes = bytes;
        error = '';
        reportText = '';
        learningText = '';
        subjectsText = '';
      });
      await analisarSelecionado(setLocalState);
    }

    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setLocalState) {
            Future<void> analisar() async => analisarSelecionado(setLocalState);

            Future<void> exportarPdf() async {
              if (reportText.trim().isEmpty) {
                setLocalState(
                    () => error = 'Gere o relatório antes de exportar.');
                return;
              }
              setLocalState(() {
                loading = true;
                error = '';
              });
              try {
                final bytes = await _buildDocumentReportPdf(
                  reportText: reportText,
                  fileName: selectedName,
                );
                final nomeBase = selectedName.trim().isEmpty
                    ? 'relatorio_documento'
                    : selectedName
                        .trim()
                        .replaceAll(RegExp(r'[^a-zA-Z0-9._-]'), '_');
                await Printing.layoutPdf(
                  name: '${nomeBase}_nova.pdf',
                  onLayout: (_) async => bytes,
                );
              } catch (_) {
                setLocalState(() => error = 'Falha ao exportar PDF.');
              } finally {
                if (context.mounted) setLocalState(() => loading = false);
              }
            }

            return NovaPanelDialog(
              title: 'ANÁLISE DE DOCUMENTOS',
              child: SizedBox(
                width: 760,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            selectedName.isEmpty
                                ? 'Nenhum arquivo selecionado'
                                : 'Arquivo: $selectedName',
                            style: const TextStyle(color: Color(0xFFBCE8FF)),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        OutlinedButton.icon(
                          onPressed: loading
                              ? null
                              : () => selecionarArquivo(setLocalState),
                          icon: const Icon(Icons.attach_file, size: 16),
                          label: const Text('Anexar'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        onPressed: loading ? null : analisar,
                        icon: loading
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child:
                                    CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.analytics_outlined),
                        label: Text(loading
                            ? 'Analisando...'
                            : 'Gerar relatório completo'),
                      ),
                    ),
                    if (learningText.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(
                        learningText,
                        style: const TextStyle(color: Color(0xFF8EE0FF)),
                      ),
                    ],
                    if (subjectsText.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(
                        subjectsText,
                        style: const TextStyle(
                            color: Color(0xFF87CFEA), fontSize: 12),
                      ),
                    ],
                    const SizedBox(height: 8),
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton.icon(
                        onPressed: loading ? null : exportarPdf,
                        icon: const Icon(Icons.picture_as_pdf_outlined),
                        label: const Text('Exportar relatório em PDF'),
                      ),
                    ),
                    if (error.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(error,
                          style: const TextStyle(color: Color(0xFFFF8A8A))),
                    ],
                    const SizedBox(height: 10),
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxHeight: 420),
                      child: SingleChildScrollView(
                        child: Text(
                          reportText.isEmpty
                              ? 'Anexe um documento e clique em "Gerar relatório completo".'
                              : reportText,
                          style: const TextStyle(
                            color: Color(0xFFD4F4FF),
                            fontSize: 12,
                            height: 1.35,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _openHelpDialog() async {
    List<Map<String, dynamic>> topics = [];
    List<Map<String, dynamic>> commands = [];
    String error = '';
    bool loading = false;
    bool isAdvancedItem(String raw) {
      final v = raw.toLowerCase();
      return v.contains('autonomia') ||
          v.contains('observabilidade') ||
          v.contains('rag') ||
          v.contains('agente') ||
          v.contains('auditoria') ||
          v.contains('sess') ||
          v.contains('assunto');
    }

    Future<void> carregar(StateSetter setLocalState) async {
      setLocalState(() {
        loading = true;
        error = '';
      });
      try {
        final out = await _api.getHelpTopics();
        final t = out['topics'];
        final c = out['commands'];
        setLocalState(() {
          topics = (t is List)
              ? t
                  .whereType<Map>()
                  .where((e) =>
                      !isAdvancedItem('${e['topic'] ?? ''} ${e['text'] ?? ''}'))
                  .map((e) => Map<String, dynamic>.from(e))
                  .toList()
              : [];
          commands = (c is List)
              ? c
                  .whereType<Map>()
                  .where((e) =>
                      !isAdvancedItem('${e['cmd'] ?? ''} ${e['desc'] ?? ''}'))
                  .map((e) => Map<String, dynamic>.from(e))
                  .toList()
              : [];
        });
      } catch (_) {
        setLocalState(() {
          error = 'Sem backend agora. Exibindo ajuda local.';
          topics = [
            {
              'topic': 'Identidade',
              'text':
                  'A NOVA é uma assistente de IA com memória, voz, RAG, automações seguras e aprendizado por documentos.',
            },
          ];
          commands = [
            {'cmd': '/help', 'desc': 'Mostra ajuda completa.'},
            {
              'cmd': '/status sistema',
              'desc': 'Status de software e segurança.'
            },
            {'cmd': '/rag <pergunta>', 'desc': 'Consulta base RAG.'},
            {
              'cmd': 'pesquise no Maps por ...',
              'desc': 'Atalho local por voz/texto para abrir busca no Maps.'
            },
            {
              'cmd': 'pesquise no YouTube por ...',
              'desc': 'Atalho local por voz/texto para abrir busca no YouTube.'
            },
            {'cmd': '/lembrar ...', 'desc': 'Cria lembrete com data/hora.'},
          ];
        });
      } finally {
        setLocalState(() => loading = false);
      }
    }

    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setLocalState) {
            if (topics.isEmpty && commands.isEmpty && !loading) {
              carregar(setLocalState);
            }
            return NovaPanelDialog(
              title: 'HELP • NOVA',
              child: SizedBox(
                width: 820,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      children: [
                        const Expanded(
                          child: Text(
                            'Guia completo por tópicos e comandos',
                            style: TextStyle(
                              color: Color(0xFFBCE8FF),
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        OutlinedButton.icon(
                          onPressed:
                              loading ? null : () => carregar(setLocalState),
                          icon: const Icon(Icons.refresh, size: 16),
                          label: Text(loading ? 'Atualizando...' : 'Atualizar'),
                        ),
                      ],
                    ),
                    if (error.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(error,
                          style: const TextStyle(color: Color(0xFFE8BC75))),
                    ],
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: _boxDeco,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Tópicos',
                            style: TextStyle(
                              color: Color(0xFFBDE8FF),
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 8),
                          ...topics.map(
                            (t) => Padding(
                              padding: const EdgeInsets.only(bottom: 8),
                              child: Text(
                                '• ${t['topic'] ?? '-'}: ${t['text'] ?? ''}',
                                style: const TextStyle(
                                  color: Color(0xFFD4F4FF),
                                  fontSize: 12,
                                  height: 1.35,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: _boxDeco,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Comandos',
                            style: TextStyle(
                              color: Color(0xFFBDE8FF),
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 8),
                          ConstrainedBox(
                            constraints: const BoxConstraints(maxHeight: 320),
                            child: ListView.separated(
                              shrinkWrap: true,
                              itemCount: commands.length,
                              separatorBuilder: (_, __) =>
                                  const SizedBox(height: 6),
                              itemBuilder: (context, index) {
                                final c = commands[index];
                                return Text(
                                  '• ${c['cmd'] ?? '-'}: ${c['desc'] ?? ''}',
                                  style: const TextStyle(
                                    color: Color(0xFFCBEFFF),
                                    fontSize: 12,
                                    height: 1.35,
                                  ),
                                );
                              },
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _executeCommand(String rawMessage,
      {required bool fromVoice}) async {
    final message = rawMessage.trim();
    if (message.isEmpty) return;

    if (fromVoice) {
      _manualListeningStop = true;
      try {
        await _speech.stop();
      } catch (_) {
        // Evita conflito de áudio em aparelhos mais sensíveis.
      }
      if (mounted) {
        setState(() => _isListening = false);
      }
    }

    setState(() {
      _chat.add(NovaChatLine(fromUser: true, text: message));
      _messageController.clear();
      _sending = true;
      _systemStatus =
          fromVoice ? 'Comando de voz enviado.' : 'Mensagem enviada.';
    });

    try {
      final localReply = await _handleLocalUiCommands(message);
      final reply = localReply ?? await _api.sendMessage(message);
      if (!mounted) return;
      setState(() {
        _chat.add(NovaChatLine(fromUser: false, text: reply));
        _systemStatus = 'Resposta recebida.';
      });
      await _speak(reply);
      await _refreshAdminState();
      await _loadReminders();
      await _refreshJarvisFoundation();
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _chat.add(
          const NovaChatLine(
            fromUser: false,
            text: 'Falha ao conectar com a API da NOVA.',
          ),
        );
        _systemStatus = 'Erro de conexão.';
      });
    } finally {
      if (mounted) {
        setState(() => _sending = false);
      }
    }
  }

  Future<void> _openTeachDialog() async {
    final allowed = await _ensureAdminAccess();
    if (!mounted) return;
    if (!allowed) {
      _showSnack('Acesso administrativo negado.');
      return;
    }
    final triggerController = TextEditingController();
    final responseController = TextEditingController();
    final categoryController = TextEditingController(text: 'geral');

    final saved = await showDialog<bool>(
      context: context,
      builder: (context) {
        return NovaPanelDialog(
          title: 'ENSINAR NOVA',
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Ensine a NOVA a responder de um jeito específico.',
                style: TextStyle(color: Color(0xFF6B98B8), fontSize: 13),
              ),
              const SizedBox(height: 14),
              const NovaFieldLabel('GATILHO (o que o usuário diz)'),
              const SizedBox(height: 8),
              NovaInput(
                  controller: triggerController,
                  hintText: 'Ex: qual seu nome?'),
              const SizedBox(height: 14),
              const NovaFieldLabel('RESPOSTA DA NOVA'),
              const SizedBox(height: 8),
              NovaInput(
                controller: responseController,
                hintText: 'Ex: Meu nome é NOVA...',
                maxLines: 4,
              ),
              const SizedBox(height: 14),
              const NovaFieldLabel('CATEGORIA'),
              const SizedBox(height: 8),
              NovaInput(controller: categoryController, hintText: 'geral'),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: () async {
                    final gatilho = triggerController.text.trim();
                    final resposta = responseController.text.trim();
                    final categoria = categoryController.text.trim().isEmpty
                        ? 'geral'
                        : categoryController.text.trim();

                    if (gatilho.isEmpty || resposta.isEmpty) return;

                    try {
                      final items = await _api.createKnowledge(
                        gatilho: gatilho,
                        resposta: resposta,
                        categoria: categoria,
                      );
                      if (!mounted) return;
                      setState(() => _knowledge = items);
                      await _saveLocalState();
                      if (!context.mounted) return;
                      Navigator.of(context).pop(true);
                    } catch (_) {
                      if (!context.mounted) return;
                      Navigator.of(context).pop(false);
                    }
                  },
                  child: const Text('ENSINAR NOVA'),
                ),
              ),
            ],
          ),
        );
      },
    );

    triggerController.dispose();
    responseController.dispose();
    categoryController.dispose();

    if (saved == true) {
      _showSnack('Novo ensinamento salvo no banco local e backend.');
    } else if (saved == false) {
      _showSnack('Não foi possível salvar ensinamento.');
    }
  }

  Future<void> _openKnowledgeDialog() async {
    final allowed = await _ensureAdminAccess();
    if (!mounted) return;
    if (!allowed) {
      _showSnack('Acesso administrativo negado.');
      return;
    }
    await showDialog<void>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setLocalState) {
            Future<void> refreshList() async {
              final items = await _api.getKnowledge();
              if (!mounted) return;
              setState(() => _knowledge = items);
              setLocalState(() {});
              await _saveLocalState();
            }

            Future<void> editItem(Map<String, dynamic> item) async {
              final triggerCtrl = TextEditingController(
                  text: item['gatilho']?.toString() ?? '');
              final responseCtrl = TextEditingController(
                  text: item['resposta']?.toString() ?? '');
              final catCtrl = TextEditingController(
                  text: item['categoria']?.toString() ?? 'geral');

              final confirmed = await showDialog<bool>(
                context: context,
                builder: (context) {
                  return NovaPanelDialog(
                    title: 'EDITAR ITEM',
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        NovaInput(controller: triggerCtrl, hintText: 'Gatilho'),
                        const SizedBox(height: 10),
                        NovaInput(
                            controller: responseCtrl,
                            hintText: 'Resposta',
                            maxLines: 3),
                        const SizedBox(height: 10),
                        NovaInput(controller: catCtrl, hintText: 'Categoria'),
                        const SizedBox(height: 14),
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton(
                            onPressed: () => Navigator.of(context).pop(true),
                            child: const Text('Salvar'),
                          ),
                        ),
                      ],
                    ),
                  );
                },
              );

              triggerCtrl.dispose();
              responseCtrl.dispose();
              catCtrl.dispose();

              if (confirmed != true) return;
              final id = item['id']?.toString() ?? '';
              if (id.isEmpty) return;

              try {
                await _api.updateKnowledge(
                  id,
                  gatilho: triggerCtrl.text.trim(),
                  resposta: responseCtrl.text.trim(),
                  categoria: catCtrl.text.trim().isEmpty
                      ? 'geral'
                      : catCtrl.text.trim(),
                );
                await refreshList();
              } catch (_) {
                _showSnack('Falha ao editar item.');
              }
            }

            Future<void> deleteItem(Map<String, dynamic> item) async {
              final id = item['id']?.toString() ?? '';
              if (id.isEmpty) return;
              try {
                final items = await _api.deleteKnowledge(id);
                if (!mounted) return;
                setState(() => _knowledge = items);
                setLocalState(() {});
                await _saveLocalState();
              } catch (_) {
                _showSnack('Falha ao remover item.');
              }
            }

            return NovaPanelDialog(
              title: 'BASE DE CONHECIMENTO',
              actions: [
                TextButton.icon(
                  onPressed: () async {
                    Navigator.of(context).pop();
                    await _openTeachDialog();
                  },
                  icon: const Icon(Icons.add),
                  label: const Text('Novo'),
                ),
              ],
              child: SizedBox(
                width: 620,
                child: _knowledge.isEmpty
                    ? const Padding(
                        padding: EdgeInsets.symmetric(vertical: 28),
                        child: Center(
                          child: Text(
                            'Nenhum ensinamento ainda.\nUse "Ensinar" para começar.',
                            textAlign: TextAlign.center,
                            style: TextStyle(color: Color(0xFF4D7694)),
                          ),
                        ),
                      )
                    : ConstrainedBox(
                        constraints: const BoxConstraints(maxHeight: 380),
                        child: ListView.separated(
                          shrinkWrap: true,
                          itemCount: _knowledge.length,
                          separatorBuilder: (_, __) =>
                              const SizedBox(height: 8),
                          itemBuilder: (context, index) {
                            final item = _knowledge[index];
                            return Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: const Color(0x66001423),
                                borderRadius: BorderRadius.circular(12),
                                border:
                                    Border.all(color: const Color(0xFF054E7A)),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    item['gatilho']?.toString() ?? '-',
                                    style: const TextStyle(
                                      color: Color(0xFFBDEBFF),
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    item['resposta']?.toString() ?? '-',
                                    style: const TextStyle(
                                        color: Color(0xFF8DB8D4)),
                                  ),
                                  const SizedBox(height: 10),
                                  Row(
                                    children: [
                                      Text(
                                        'Categoria: ${item['categoria'] ?? 'geral'}',
                                        style: const TextStyle(
                                          color: Color(0xFF2FD0FF),
                                          fontSize: 12,
                                        ),
                                      ),
                                      const Spacer(),
                                      IconButton(
                                        onPressed: () => editItem(item),
                                        icon: const Icon(Icons.edit, size: 18),
                                      ),
                                      IconButton(
                                        onPressed: () => deleteItem(item),
                                        icon: const Icon(Icons.delete_outline,
                                            size: 18),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                      ),
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _openUsersDialog() async {
    final allowed = await _ensureAdminAccess();
    if (!mounted) return;
    if (!allowed) {
      _showSnack('Acesso administrativo negado.');
      return;
    }
    final newUserController = TextEditingController();

    await showDialog<void>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setLocalState) {
            Future<void> addUser() async {
              final name = newUserController.text.trim();
              if (name.isEmpty) return;
              try {
                final users = await _api.addUser(name);
                if (!mounted) return;
                setState(() => _users = users);
                newUserController.clear();
                setLocalState(() {});
                await _saveLocalState();
              } catch (_) {
                _showSnack('Falha ao adicionar usuário.');
              }
            }

            Future<void> toggleUser(Map<String, dynamic> user) async {
              final id = user['id']?.toString() ?? '';
              if (id.isEmpty) return;
              final current = user['ativo'] == true;
              try {
                final users = await _api.updateUser(id, active: !current);
                if (!mounted) return;
                setState(() => _users = users);
                setLocalState(() {});
                await _saveLocalState();
              } catch (_) {
                _showSnack('Falha ao atualizar usuário.');
              }
            }

            Future<void> removeUser(Map<String, dynamic> user) async {
              final id = user['id']?.toString() ?? '';
              if (id.isEmpty) return;
              try {
                final users = await _api.deleteUser(id);
                if (!mounted) return;
                setState(() => _users = users);
                setLocalState(() {});
                await _saveLocalState();
              } catch (_) {
                _showSnack('Falha ao remover usuário.');
              }
            }

            return NovaPanelDialog(
              title: 'GERENCIAR USUÁRIOS',
              child: SizedBox(
                width: 620,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: NovaInput(
                            controller: newUserController,
                            hintText: 'Nome do novo usuário...',
                          ),
                        ),
                        const SizedBox(width: 10),
                        FilledButton.icon(
                          onPressed: addUser,
                          icon: const Icon(Icons.add),
                          label: const Text('Adicionar'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    if (_users.isEmpty)
                      const Padding(
                        padding: EdgeInsets.all(10),
                        child: Text(
                          'Sem usuários cadastrados.',
                          style: TextStyle(color: Color(0xFF6889A2)),
                        ),
                      )
                    else
                      ConstrainedBox(
                        constraints: const BoxConstraints(maxHeight: 340),
                        child: ListView.separated(
                          shrinkWrap: true,
                          itemCount: _users.length,
                          separatorBuilder: (_, __) =>
                              const SizedBox(height: 8),
                          itemBuilder: (context, index) {
                            final user = _users[index];
                            final active = user['ativo'] == true;
                            return Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 12, vertical: 10),
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(12),
                                color: const Color(0x55001423),
                                border:
                                    Border.all(color: const Color(0xFF05507D)),
                              ),
                              child: Row(
                                children: [
                                  CircleAvatar(
                                    radius: 16,
                                    backgroundColor: const Color(0xFF00C8FF)
                                        .withValues(alpha: 0.2),
                                    child: Text(
                                      (user['nome']
                                                  ?.toString()
                                                  .trim()
                                                  .isNotEmpty ??
                                              false)
                                          ? user['nome']
                                              .toString()
                                              .trim()
                                              .substring(0, 1)
                                              .toUpperCase()
                                          : 'U',
                                      style: const TextStyle(
                                          color: Color(0xFF00D1FF)),
                                    ),
                                  ),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          user['nome']?.toString() ?? '-',
                                          style: const TextStyle(
                                            color: Color(0xFFD7F4FF),
                                            fontWeight: FontWeight.w600,
                                          ),
                                        ),
                                        Text(
                                          '${user['papel'] ?? 'usuario'} · desde ${user['desde'] ?? '-'}',
                                          style: const TextStyle(
                                              color: Color(0xFF5F8AA8),
                                              fontSize: 12),
                                        ),
                                      ],
                                    ),
                                  ),
                                  TextButton(
                                    onPressed: () => toggleUser(user),
                                    child: Text(
                                      active ? 'ATIVO' : 'INATIVO',
                                      style: TextStyle(
                                        color: active
                                            ? const Color(0xFF00DCFF)
                                            : const Color(0xFF7A8D9C),
                                      ),
                                    ),
                                  ),
                                  IconButton(
                                    onPressed: () => removeUser(user),
                                    icon: const Icon(Icons.close, size: 18),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                      ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );

    newUserController.dispose();
  }

  Future<void> _openConfigDialog() async {
    final allowed = await _ensureAdminAccess();
    if (!mounted) return;
    if (!allowed) {
      _showSnack('Acesso administrativo negado.');
      return;
    }
    final wakeWordController = TextEditingController(
      text: _config['wake_word']?.toString() ?? 'nova',
    );
    final telegramTokenController = TextEditingController(
      text: _config['telegram_token']?.toString() ?? '',
    );
    final telegramChatController = TextEditingController(
      text: _config['telegram_chat_id']?.toString() ?? '',
    );
    bool vozAtiva = _config['voz_ativa'] == true;
    bool vozNeuralHybrid = _config['voice_neural_hybrid'] != false;
    String voiceProfile =
        _config['voice_profile']?.toString().trim().toLowerCase() ?? 'feminina';
    bool escutaAtiva = _config['escuta_ativa'] != false;
    bool telegramAtivo = _config['telegram_ativo'] == true;
    bool wakeContinuo = _config['continuous_wake'] != false;
    bool pushToTalkOnly = _config['push_to_talk_only'] != false;
    bool autoDocumentLearning = _config['auto_document_learning'] != false;
    bool adminGuard = _config['admin_guard'] != false;
    bool allowVoiceOnLock = _config['allow_voice_on_lock'] != false;

    await showDialog<void>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setLocalState) {
            Future<void> salvarConfig() async {
              final wakeContinuoEfetivo = pushToTalkOnly ? false : wakeContinuo;
              final novo = {
                'voz_ativa': vozAtiva,
                'voice_neural_hybrid': vozNeuralHybrid,
                'voice_profile': voiceProfile,
                'escuta_ativa': escutaAtiva,
                'wake_word': wakeWordController.text.trim().isEmpty
                    ? 'nova'
                    : wakeWordController.text.trim(),
                'continuous_wake': wakeContinuoEfetivo,
                'push_to_talk_only': pushToTalkOnly,
                'telegram_ativo': telegramAtivo,
                'telegram_token': telegramTokenController.text.trim(),
                'telegram_chat_id': telegramChatController.text.trim(),
                'auto_document_learning': autoDocumentLearning,
                'admin_guard': adminGuard,
                'allow_voice_on_lock': allowVoiceOnLock,
              };

              try {
                final atualizado = await _api.updateConfig(novo);
                if (!mounted) return;
                setState(() {
                  _config = {..._config, ...novo, ...atualizado};
                  _continuousWakeMode = _config['continuous_wake'] != false;
                  if (_pushToTalkOnly) {
                    _continuousWakeMode = false;
                  }
                });
                if (!escutaAtiva) {
                  _manualListeningStop = true;
                  await _speech.stop();
                  await BackgroundWakeService.stop();
                  if (mounted) {
                    setState(() => _isListening = false);
                  }
                } else if (!_effectiveContinuousWake && _isListening) {
                  _manualListeningStop = true;
                  await _speech.stop();
                }
                if (escutaAtiva && _effectiveContinuousWake && !_isListening) {
                  _manualListeningStop = false;
                  await _startListening();
                }
                await _saveLocalState();
                if (!context.mounted) return;
                Navigator.of(context).pop();
                _showSnack('Configurações salvas com sucesso.');
              } catch (_) {
                if (!mounted) return;
                setState(() {
                  _config = {..._config, ...novo};
                  _continuousWakeMode = _config['continuous_wake'] != false;
                  if (_pushToTalkOnly) {
                    _continuousWakeMode = false;
                  }
                });
                await _saveLocalState();
                if (!context.mounted) return;
                Navigator.of(context).pop();
                _showSnack(
                  'Configurações salvas localmente (sem backend no momento).',
                );
              }
            }

            Future<void> definirPinAdmin() async {
              final pin1 = TextEditingController();
              final pin2 = TextEditingController();
              await showDialog<void>(
                context: context,
                builder: (context) {
                  return AlertDialog(
                    backgroundColor: const Color(0xFF021526),
                    title: const Text('Definir PIN administrativo'),
                    content: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        TextField(
                          controller: pin1,
                          keyboardType: TextInputType.number,
                          obscureText: true,
                          maxLength: 8,
                          decoration: const InputDecoration(
                            hintText: 'Novo PIN (4-8 dígitos)',
                            counterText: '',
                          ),
                        ),
                        const SizedBox(height: 8),
                        TextField(
                          controller: pin2,
                          keyboardType: TextInputType.number,
                          obscureText: true,
                          maxLength: 8,
                          decoration: const InputDecoration(
                            hintText: 'Confirmar PIN',
                            counterText: '',
                          ),
                        ),
                      ],
                    ),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.of(context).pop(),
                        child: const Text('Cancelar'),
                      ),
                      FilledButton(
                        onPressed: () async {
                          final a = pin1.text.trim();
                          final b = pin2.text.trim();
                          if (a.length < 4 || a.length > 8) {
                            _showSnack('PIN deve ter entre 4 e 8 dígitos.');
                            return;
                          }
                          if (a != b) {
                            _showSnack('PINs não conferem.');
                            return;
                          }
                          await _secureSecrets.setAdminPin(a);
                          if (context.mounted) Navigator.of(context).pop();
                          _showSnack('PIN administrativo atualizado.');
                        },
                        child: const Text('Salvar PIN'),
                      ),
                    ],
                  );
                },
              );
              pin1.dispose();
              pin2.dispose();
            }

            return NovaPanelDialog(
              title: 'CONFIGURAÇÕES',
              child: SizedBox(
                width: 620,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: _boxDeco,
                      child: Row(
                        children: [
                          const Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('Voz da NOVA',
                                    style:
                                        TextStyle(fontWeight: FontWeight.w600)),
                                SizedBox(height: 2),
                                Text(
                                  'Respostas em áudio',
                                  style: TextStyle(
                                      color: Color(0xFF6689A2), fontSize: 12),
                                ),
                              ],
                            ),
                          ),
                          Switch.adaptive(
                            value: vozAtiva,
                            onChanged: (value) {
                              vozAtiva = value;
                              setLocalState(() {});
                            },
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: _boxDeco,
                      child: Row(
                        children: [
                          const Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('Aprendizado por documentos',
                                    style:
                                        TextStyle(fontWeight: FontWeight.w600)),
                                SizedBox(height: 2),
                                Text(
                                  'Quando um arquivo é analisado, a NOVA aprende automaticamente e atualiza a base.',
                                  style: TextStyle(
                                      color: Color(0xFF6689A2), fontSize: 12),
                                ),
                              ],
                            ),
                          ),
                          Switch.adaptive(
                            value: autoDocumentLearning,
                            onChanged: (value) {
                              autoDocumentLearning = value;
                              setLocalState(() {});
                            },
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: _boxDeco,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text('Voz Neural Híbrida',
                                        style: TextStyle(
                                            fontWeight: FontWeight.w600)),
                                    SizedBox(height: 2),
                                    Text(
                                      'Usa voz neural online e cai para voz local se estiver offline',
                                      style: TextStyle(
                                          color: Color(0xFF6689A2),
                                          fontSize: 12),
                                    ),
                                  ],
                                ),
                              ),
                              Switch.adaptive(
                                value: vozNeuralHybrid,
                                onChanged: (value) {
                                  vozNeuralHybrid = value;
                                  setLocalState(() {});
                                },
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          DropdownButtonFormField<String>(
                            initialValue: ['feminina', 'francisca', 'thalita']
                                    .contains(voiceProfile)
                                ? voiceProfile
                                : 'feminina',
                            decoration: const InputDecoration(
                              labelText: 'Perfil de voz',
                              border: OutlineInputBorder(),
                            ),
                            items: const [
                              DropdownMenuItem(
                                value: 'feminina',
                                child: Text('Feminina (recomendado)'),
                              ),
                              DropdownMenuItem(
                                value: 'francisca',
                                child: Text('Francisca'),
                              ),
                              DropdownMenuItem(
                                value: 'thalita',
                                child: Text('Thalita'),
                              ),
                            ],
                            onChanged: (value) {
                              voiceProfile = (value ?? 'feminina').trim();
                              setLocalState(() {});
                            },
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: _boxDeco,
                      child: Row(
                        children: [
                          const Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('Modo Escuta',
                                    style:
                                        TextStyle(fontWeight: FontWeight.w600)),
                                SizedBox(height: 2),
                                Text(
                                  'Liga/desliga captação do microfone da assistente',
                                  style: TextStyle(
                                      color: Color(0xFF6689A2), fontSize: 12),
                                ),
                              ],
                            ),
                          ),
                          Switch.adaptive(
                            value: escutaAtiva,
                            onChanged: (value) {
                              escutaAtiva = value;
                              if (!escutaAtiva) {
                                wakeContinuo = false;
                              }
                              setLocalState(() {});
                            },
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: _boxDeco,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Expanded(
                                child: Text('Segurança Administrativa',
                                    style:
                                        TextStyle(fontWeight: FontWeight.w600)),
                              ),
                              Switch.adaptive(
                                value: adminGuard,
                                onChanged: (value) {
                                  adminGuard = value;
                                  setLocalState(() {});
                                },
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          const Text(
                            'Bloqueia telas administrativas com biometria/PIN e guarda segredos em cofre seguro.',
                            style: TextStyle(
                              color: Color(0xFF6689A2),
                              fontSize: 12,
                            ),
                          ),
                          const SizedBox(height: 10),
                          Row(
                            children: [
                              const Expanded(
                                child: Text(
                                  'Permitir comando de voz com tela bloqueada',
                                  style: TextStyle(
                                      color: Color(0xFF6689A2), fontSize: 12),
                                ),
                              ),
                              Switch.adaptive(
                                value: allowVoiceOnLock,
                                onChanged: (value) {
                                  allowVoiceOnLock = value;
                                  setLocalState(() {});
                                },
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          SizedBox(
                            width: double.infinity,
                            child: OutlinedButton(
                              onPressed: definirPinAdmin,
                              child: const Text('Definir/alterar PIN admin'),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: _boxDeco,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Wake Word',
                              style: TextStyle(fontWeight: FontWeight.w600)),
                          const SizedBox(height: 6),
                          NovaInput(
                              controller: wakeWordController, hintText: 'nova'),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              const Expanded(
                                child: Text(
                                  'Modo manual (push-to-talk)',
                                  style: TextStyle(
                                      color: Color(0xFF6689A2), fontSize: 12),
                                ),
                              ),
                              Switch.adaptive(
                                value: pushToTalkOnly,
                                onChanged: (value) {
                                  pushToTalkOnly = value;
                                  if (pushToTalkOnly) {
                                    wakeContinuo = false;
                                  }
                                  setLocalState(() {});
                                },
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              const Expanded(
                                child: Text(
                                  'Monitor de voz contínuo',
                                  style: TextStyle(
                                      color: Color(0xFF6689A2), fontSize: 12),
                                ),
                              ),
                              Switch.adaptive(
                                value: escutaAtiva && !pushToTalkOnly
                                    ? wakeContinuo
                                    : false,
                                onChanged: (value) {
                                  if (!escutaAtiva || pushToTalkOnly) return;
                                  wakeContinuo = value;
                                  setLocalState(() {});
                                },
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: _boxDeco,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Expanded(
                                child: Text('Telegram',
                                    style:
                                        TextStyle(fontWeight: FontWeight.w600)),
                              ),
                              Switch.adaptive(
                                value: telegramAtivo,
                                onChanged: (value) {
                                  telegramAtivo = value;
                                  setLocalState(() {});
                                },
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          NovaInput(
                              controller: telegramTokenController,
                              hintText: 'Bot Token'),
                          const SizedBox(height: 8),
                          NovaInput(
                              controller: telegramChatController,
                              hintText: 'Chat ID'),
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton(
                        onPressed: () {
                          setState(() {
                            _chat.clear();
                            _systemStatus = 'Histórico limpo.';
                          });
                        },
                        style: OutlinedButton.styleFrom(
                          foregroundColor: const Color(0xFFFF6262),
                          side: const BorderSide(color: Color(0xFF7A2A2A)),
                        ),
                        child: const Text('Limpar histórico de chat'),
                      ),
                    ),
                    const SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton(
                        onPressed: salvarConfig,
                        child: const Text('Salvar configurações'),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );

    wakeWordController.dispose();
    telegramTokenController.dispose();
    telegramChatController.dispose();
  }

  void _showSnack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        behavior: SnackBarBehavior.floating,
        backgroundColor: const Color(0xFF042338),
      ),
    );
  }

  String _humanizeApiError(
    Object error, {
    String fallback = 'Falha ao comunicar com a API.',
  }) {
    var raw = error.toString().trim();
    raw = raw.replaceFirst('Exception: ', '');
    raw = raw.replaceFirst('ApiHttpException: ', '');
    if (raw.isEmpty) return fallback;
    if (raw.contains('Endpoint não encontrado nesse backend') ||
        raw.contains('não possui a rota de autonomia')) {
      return '$raw\n\nDica: atualize/deploy o backend mais recente e '
          'recompile o app com NOVA_API_URL correto.';
    }
    if (raw.contains('Falha de conexão com a API')) {
      return 'Sem conexão com a API. Verifique URL do backend, internet e porta.';
    }
    return raw;
  }

  BoxDecoration get _boxDeco {
    return BoxDecoration(
      color: const Color(0x4D03192A),
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: const Color(0xFF07456A)),
    );
  }

  Future<void> _openQuickMenu() async {
    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF021626),
      showDragHandle: true,
      builder: (context) {
        final actions = <({String label, IconData icon, VoidCallback onTap})>[
          (
            label: 'Ensinar',
            icon: Icons.school_outlined,
            onTap: _openTeachDialog
          ),
          (
            label: 'Editar Base',
            icon: Icons.edit_note,
            onTap: _openKnowledgeDialog
          ),
          (label: 'Lembretes', icon: Icons.alarm, onTap: _openRemindersDialog),
          (
            label: 'Documentos',
            icon: Icons.description_outlined,
            onTap: _openDocumentAnalysisDialog
          ),
          (label: 'Help', icon: Icons.help_outline, onTap: _openHelpDialog),
          (
            label: 'Compatibilidade',
            icon: Icons.devices,
            onTap: _openCompatibilityDialog
          ),
          (
            label: 'Configurações',
            icon: Icons.settings_outlined,
            onTap: _openConfigDialog
          ),
        ];

        return LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 560;
            final maxHeight = MediaQuery.sizeOf(context).height * 0.8;
            return SafeArea(
              child: ConstrainedBox(
                constraints: BoxConstraints(maxHeight: maxHeight),
                child: compact
                    ? ListView.separated(
                        shrinkWrap: true,
                        itemCount: actions.length,
                        separatorBuilder: (_, __) =>
                            const Divider(height: 1, color: Color(0x220A446A)),
                        itemBuilder: (context, index) {
                          final item = actions[index];
                          return ListTile(
                            leading:
                                Icon(item.icon, color: const Color(0xFF6CD2FF)),
                            title: Text(
                              item.label,
                              style: const TextStyle(color: Color(0xFFD2F2FF)),
                            ),
                            onTap: () {
                              Navigator.of(context).pop();
                              item.onTap();
                            },
                          );
                        },
                      )
                    : GridView.builder(
                        shrinkWrap: true,
                        padding: const EdgeInsets.fromLTRB(14, 6, 14, 14),
                        gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: constraints.maxWidth >= 1100
                              ? 4
                              : (constraints.maxWidth >= 760 ? 3 : 2),
                          mainAxisSpacing: 10,
                          crossAxisSpacing: 10,
                          childAspectRatio:
                              constraints.maxWidth >= 1100 ? 3.1 : 2.8,
                        ),
                        itemCount: actions.length,
                        itemBuilder: (context, index) {
                          final item = actions[index];
                          return OutlinedButton.icon(
                            onPressed: () {
                              Navigator.of(context).pop();
                              item.onTap();
                            },
                            icon: Icon(item.icon, size: 18),
                            label: Align(
                              alignment: Alignment.centerLeft,
                              child: Text(item.label,
                                  maxLines: 1, overflow: TextOverflow.ellipsis),
                            ),
                            style: OutlinedButton.styleFrom(
                              foregroundColor: const Color(0xFFD2F2FF),
                              side: const BorderSide(color: Color(0xFF0A446A)),
                              backgroundColor: const Color(0x4403182A),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(10),
                              ),
                            ),
                          );
                        },
                      ),
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildMainColumn({
    required bool compact,
    required bool compressed,
    bool wideChat = false,
  }) {
    final topGap = compressed ? 8.0 : 12.0;
    final composerGap = compressed ? 8.0 : 10.0;
    return Column(
      children: [
        NovaTopBar(
          onOpenQuickMenu: _openQuickMenu,
          onOpenUsersDialog: _openUsersDialog,
          onPickQuickPhoto: _pickQuickPhoto,
          compact: compact,
          compressed: compressed,
        ),
        SizedBox(height: topGap),
        Expanded(
          child: NovaChatTimeline(
            chat: _chat,
            compact: compact,
            wide: wideChat,
          ),
        ),
        SizedBox(height: composerGap),
        NovaComposer(
          messageController: _messageController,
          composerAttachmentName: _composerAttachmentName,
          speechReady: _speechReady,
          isListening: _isListening,
          sending: _sending,
          compact: compact,
          compressed: compressed,
          onPickComposerAttachment: _pickComposerAttachment,
          onToggleListening: _toggleListening,
          onInitSpeech: () {
            _initSpeech();
          },
          onSendMessage: _handleSendMessage,
        ),
      ],
    );
  }

  List<String> _projectExamples() {
    return const [
      'Nova, crie um projeto chamado Atlas Comercial na área Comercial',
      'Novo projeto "Portal do Cliente" com prioridade alta',
      'Crie um projeto com descrição MVP B2B e link https://exemplo.com',
    ];
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.sizeOf(context).width;
    final shellMaxWidth = screenWidth >= 1500
        ? 860.0
        : (screenWidth >= 1200
            ? 760.0
            : (screenWidth >= 900
                ? 680.0
                : (screenWidth >= 600 ? 560.0 : screenWidth)));
    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          const NovaGridBackground(),
          SafeArea(
            child: LayoutBuilder(
              builder: (context, viewport) {
                final useWideLayout = viewport.maxWidth >= 980;
                final compressed = viewport.maxHeight < 650;

                final chatShell = ConstrainedBox(
                  constraints: BoxConstraints(maxWidth: shellMaxWidth),
                  child: LayoutBuilder(
                    builder: (context, constraints) {
                      final compact = constraints.maxWidth < 560;
                      final wideChat = constraints.maxWidth >= 680;
                      return Padding(
                        padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
                        child: _buildMainColumn(
                          compact: compact,
                          compressed: compressed,
                          wideChat: wideChat,
                        ),
                      );
                    },
                  ),
                );

                if (!useWideLayout) {
                  return Center(child: chatShell);
                }

                final railWidth = viewport.maxWidth >= 1400 ? 360.0 : 320.0;
                return Padding(
                  padding: const EdgeInsets.fromLTRB(18, 12, 18, 16),
                  child: Row(
                    children: [
                      SizedBox(
                        width: railWidth,
                        child: NovaWorkspaceRail(
                          greeting: '${_periodGreeting()}!',
                          systemStatus: _systemStatus,
                          apiBaseUrl: _api.baseUrl,
                          wakeWord: _config['wake_word']
                                      ?.toString()
                                      .trim()
                                      .isNotEmpty ==
                                  true
                              ? _config['wake_word'].toString().trim()
                              : 'nova',
                          voiceEnabled: _ttsEnabled,
                          speechReady: _speechReady,
                          autonomyEnabled: _config['autonomia_ativa'] == true,
                          continuousWake: _effectiveContinuousWake,
                          examples: _projectExamples(),
                          jarvisMode: (_jarvisStatus['mode']?.toString() ??
                                  'jarvis_phase1')
                              .replaceAll('_', ' ')
                              .toUpperCase(),
                          toolsTotal: _jarvisTools.isNotEmpty
                              ? _jarvisTools.length
                              : ((_jarvisStatus['tools_total'] as num?)
                                      ?.toInt() ??
                                  0),
                          memoryItems: _memoryRailItems(),
                          toolNames: _jarvisTools
                              .map((item) =>
                                  item['name']?.toString().trim() ?? '')
                              .where((name) => name.isNotEmpty)
                              .toList(),
                          voicePhase:
                              _voiceStatus['phase']?.toString().trim() ??
                                  'planned',
                          compressed: compressed,
                        ),
                      ),
                      const SizedBox(width: 18),
                      Expanded(
                        child: Align(
                          alignment: Alignment.center,
                          child: chatShell,
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
