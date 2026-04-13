import 'dart:convert';
import 'dart:io';

import 'package:audioplayers/audioplayers.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:geolocator/geolocator.dart';
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
  final ReminderNotificationsService _notifications =
      ReminderNotificationsService();
  final SystemScanService _systemScan = SystemScanService();

  final List<_ChatLine> _chat = [];
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
    'admin_guard': true,
    'allow_voice_on_lock': true,
    'log_consciencia': <dynamic>[],
  };

  String _systemStatus = 'Conectando...';
  bool _speechReady = false;
  bool _isListening = false;
  bool _executedFromVoice = false;
  bool _sending = false;
  bool _loadingState = false;
  bool _continuousWakeMode = false;
  bool _manualListeningStop = false;
  int _speakRequestId = 0;
  bool _adminUnlocked = false;
  DateTime? _adminUnlockedAt;
  Map<String, dynamic> _marketQuotes = {};
  List<Map<String, String>> _musicLibrary = [];
  List<Map<String, dynamic>> _reminders = [];
  String _locationLabel = 'Localização não definida';
  String _locationWeather = '';
  bool _loadingLocation = false;

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
    if (_locationLabel != 'Localização não definida') {
      return '$base Aqui em $_locationLabel, pronta para te ajudar.';
    }
    return '$base Estou aqui, pronta para aprender com você e te ajudar.';
  }

  void _refreshWelcomeChatLine() {
    if (_chat.isEmpty) return;
    final first = _chat.first;
    if (first.fromUser) return;
    final txt = first.text.toLowerCase();
    if (!(txt.contains('eu sou a nova') || txt.contains('pronta para'))) return;
    setState(() {
      _chat[0] = _ChatLine(fromUser: false, text: _initialGreeting());
    });
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _chat.add(_ChatLine(fromUser: false, text: _initialGreeting()));
    _restoreLocalState();
    _initTts();
    _initSpeech();
    _refreshAdminState();
    _refreshMarketQuotes();
    _loadMusicLibrary();
    _loadReminders();
    _notifications.init();
    _loadLocationFromBackend();
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
    if (!Platform.isAndroid) return;

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

  Future<void> _loadLocationFromBackend() async {
    try {
      final loc = await _api.getCurrentLocation();
      final label = (loc['label']?.toString() ?? '').trim();
      if (!mounted) return;
      if (label.isNotEmpty) {
        setState(() => _locationLabel = label);
        _refreshWelcomeChatLine();
      }
    } catch (_) {
      // sem backend, mantém local.
    }
  }

  Future<void> _updateLocation() async {
    if (_loadingLocation) return;
    setState(() => _loadingLocation = true);
    try {
      final enabled = await Geolocator.isLocationServiceEnabled();
      if (!enabled) {
        _showSnack('Ative a localização do celular.');
        return;
      }
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        _showSnack('Permissão de localização negada.');
        return;
      }
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium,
        ),
      );
      final label =
          'Lat ${pos.latitude.toStringAsFixed(4)}, Lon ${pos.longitude.toStringAsFixed(4)}';

      String weather = '';
      try {
        weather = await _api.getWeatherByCoords(
          latitude: pos.latitude,
          longitude: pos.longitude,
        );
      } catch (_) {
        weather = '';
      }
      try {
        await _api.updateLocation(
          label: label,
          latitude: pos.latitude,
          longitude: pos.longitude,
        );
      } catch (_) {
        // backend offline
      }
      if (!mounted) return;
      setState(() {
        _locationLabel = label;
        _locationWeather = weather;
        _systemStatus = 'Localização atualizada.';
      });
      _refreshWelcomeChatLine();
    } catch (_) {
      _showSnack('Não consegui obter sua localização agora.');
    } finally {
      if (mounted) setState(() => _loadingLocation = false);
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

  Future<void> _refreshMarketQuotes() async {
    try {
      final quotes = await _api.getMarketQuotes();
      if (!mounted) return;
      setState(() => _marketQuotes = quotes);
    } catch (_) {
      // Mantém último snapshot em caso de falha.
    }
  }

  Future<void> _loadMusicLibrary() async {
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
      await _localDb.saveReminders(items);
      if (!mounted) return;
      setState(() => _reminders = items);
    } catch (_) {
      try {
        final localItems = await _localDb.getReminders();
        if (!mounted) return;
        setState(() => _reminders = localItems);
      } catch (_) {
        // mantém último estado em memória
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
        if (ok) return;
      } catch (_) {
        // fallback local abaixo
      }
    }

    if (requestId != _speakRequestId) return;
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
        _chat.add(const _ChatLine(fromUser: false, text: ack));
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
    if (message.isEmpty) return;
    await _executeCommand(message, fromVoice: false);
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
    if (t == 'abrir observabilidade' ||
        t == 'mostrar observabilidade' ||
        t == '/observabilidade') {
      _openObservabilityDialog();
      return 'Abrindo observabilidade.';
    }
    if (t == 'abrir rag feedback' ||
        t == 'mostrar rag feedback' ||
        t == '/rag-feedback') {
      _openRagFeedbackDialog();
      return 'Abrindo painel de feedback RAG.';
    }
    if (t == 'abrir agente ia' || t == 'abrir agente' || t == '/agente-ia') {
      _openAgentControlDialog();
      return 'Abrindo painel do agente IA.';
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
    if (t == 'abrir auditoria' ||
        t == 'mostrar auditoria' ||
        t == 'painel de seguranca' ||
        t == 'painel de segurança' ||
        t == '/painel-auditoria') {
      _openSecurityAuditDialog();
      return 'Abrindo painel de auditoria de segurança.';
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

  Future<void> _openSecurityAuditDialog() async {
    final allowed = await _ensureAdminAccess();
    if (!mounted) return;
    if (!allowed) {
      _showSnack('Acesso administrativo negado.');
      return;
    }

    String localReport = await _gerarVarreduraSoftwareHardware();
    Map<String, dynamic> audit = {};
    List<Map<String, dynamic>> history = [];
    String error = '';
    bool loading = false;
    try {
      audit = await _api.getSecurityAudit();
      history = await _api.getSecurityAuditHistory(limit: 24);
    } catch (_) {
      error = 'Não foi possível carregar auditoria do backend agora.';
    }

    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setLocalState) {
            Future<void> refreshAudit() async {
              setLocalState(() {
                loading = true;
                error = '';
              });
              final nextLocal = await _gerarVarreduraSoftwareHardware();
              try {
                final nextAudit = await _api.getSecurityAudit();
                final nextHistory =
                    await _api.getSecurityAuditHistory(limit: 24);
                setLocalState(() {
                  localReport = nextLocal;
                  audit = nextAudit;
                  history = nextHistory;
                });
              } catch (_) {
                setLocalState(() {
                  localReport = nextLocal;
                  error = 'Não foi possível atualizar a auditoria do backend.';
                });
              } finally {
                setLocalState(() => loading = false);
              }
            }

            final score = int.tryParse(audit['score']?.toString() ?? '') ?? 0;
            final nivel = audit['nivel']?.toString().toLowerCase() ?? 'atencao';
            final achados = (audit['achados'] is List)
                ? (audit['achados'] as List)
                : const [];
            final prioridades = (audit['prioridades'] is List)
                ? (audit['prioridades'] as List)
                : const [];

            return _PanelDialog(
              title: 'AUDITORIA DE SEGURANÇA',
              child: SizedBox(
                width: 760,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Container(
                            padding: const EdgeInsets.all(12),
                            decoration: _boxDeco,
                            child: Row(
                              children: [
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      const Text(
                                        'Score de Segurança',
                                        style: TextStyle(
                                          color: Color(0xFFAEDAF0),
                                          fontWeight: FontWeight.w700,
                                        ),
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        '$score/100',
                                        style: const TextStyle(
                                          color: Color(0xFFD6F5FF),
                                          fontSize: 26,
                                          fontWeight: FontWeight.w800,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                _AuditLevelBadge(level: nivel),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    if (error.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Text(
                          error,
                          style: const TextStyle(color: Color(0xFFFF8484)),
                        ),
                      ),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: _boxDeco,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Achados Críticos e Relevantes',
                            style: TextStyle(
                              color: Color(0xFFBDE8FF),
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 8),
                          if (achados.isEmpty)
                            const Text(
                              'Nenhum achado crítico no momento.',
                              style: TextStyle(color: Color(0xFF6EA1BE)),
                            )
                          else
                            ...achados.take(6).map((item) {
                              if (item is! Map) return const SizedBox.shrink();
                              final sev = item['severidade']?.toString() ?? '-';
                              final titulo =
                                  item['titulo']?.toString() ?? 'Achado';
                              final acao =
                                  item['acao']?.toString() ?? 'Revisar';
                              return Padding(
                                padding: const EdgeInsets.only(bottom: 6),
                                child: Text(
                                  '[$sev] $titulo -> $acao',
                                  style: const TextStyle(
                                    color: Color(0xFFD4F4FF),
                                    fontSize: 12,
                                  ),
                                ),
                              );
                            }),
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
                            'Timeline de Auditorias',
                            style: TextStyle(
                              color: Color(0xFFBDE8FF),
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 8),
                          if (history.isEmpty)
                            const Text(
                              'Sem histórico ainda. Use "Atualizar Auditoria" para registrar snapshots.',
                              style: TextStyle(color: Color(0xFF6EA1BE)),
                            )
                          else
                            ConstrainedBox(
                              constraints: const BoxConstraints(maxHeight: 180),
                              child: ListView.separated(
                                shrinkWrap: true,
                                itemCount: history.length,
                                separatorBuilder: (_, __) =>
                                    const SizedBox(height: 8),
                                itemBuilder: (context, index) {
                                  final item = history[index];
                                  return _AuditTimelineRow(item: item);
                                },
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
                            'Hardening por Prioridade',
                            style: TextStyle(
                              color: Color(0xFFBDE8FF),
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 8),
                          if (prioridades.isEmpty)
                            const Text(
                              'Sem prioridades retornadas pelo backend.',
                              style: TextStyle(color: Color(0xFF6EA1BE)),
                            )
                          else
                            ...prioridades.take(6).map(
                                  (p) => Padding(
                                    padding: const EdgeInsets.only(bottom: 6),
                                    child: Text(
                                      p.toString(),
                                      style: const TextStyle(
                                        color: Color(0xFFD4F4FF),
                                        fontSize: 12,
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
                            'Status Software/Hardware',
                            style: TextStyle(
                              color: Color(0xFFBDE8FF),
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 8),
                          ConstrainedBox(
                            constraints: const BoxConstraints(maxHeight: 180),
                            child: SingleChildScrollView(
                              child: Text(
                                localReport,
                                style: const TextStyle(
                                  color: Color(0xFF74A8C4),
                                  fontSize: 12,
                                  height: 1.4,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: loading ? null : refreshAudit,
                            icon: loading
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  )
                                : const Icon(Icons.refresh),
                            label: Text(loading
                                ? 'Atualizando...'
                                : 'Atualizar Auditoria'),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: FilledButton.icon(
                            onPressed: () {
                              Navigator.of(context).pop();
                              _openConfigDialog();
                            },
                            icon: const Icon(Icons.build_circle_outlined),
                            label: const Text('Corrigir Agora'),
                          ),
                        ),
                      ],
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

  bool _isAdminSessionValid() {
    if (!_adminUnlocked) return false;
    final at = _adminUnlockedAt;
    if (at == null) return false;
    return DateTime.now().difference(at) <= const Duration(minutes: 10);
  }

  Future<bool> _validateAdminPinFlow() async {
    final hasPin = await _secureSecrets.hasAdminPin();
    if (!hasPin || !mounted) return false;

    final pinController = TextEditingController();
    bool ok = false;

    await showDialog<void>(
      context: context,
      builder: (context) {
        return AlertDialog(
          backgroundColor: const Color(0xFF021526),
          title: const Text('PIN administrativo'),
          content: TextField(
            controller: pinController,
            keyboardType: TextInputType.number,
            obscureText: true,
            maxLength: 8,
            style: const TextStyle(color: Color(0xFFE9FAFF)),
            decoration: const InputDecoration(
              hintText: 'Digite seu PIN',
              counterText: '',
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancelar'),
            ),
            FilledButton(
              onPressed: () async {
                final valid = await _secureSecrets
                    .validateAdminPin(pinController.text.trim());
                if (valid) {
                  ok = true;
                  if (context.mounted) Navigator.of(context).pop();
                  return;
                }
                if (mounted) _showSnack('PIN inválido.');
              },
              child: const Text('Confirmar'),
            ),
          ],
        );
      },
    );
    pinController.dispose();
    return ok;
  }

  Future<bool> _ensureAdminAccess() async {
    if (_config['admin_guard'] != true) return true;
    if (_isAdminSessionValid()) return true;

    final hasPin = await _secureSecrets.hasAdminPin();
    final hasBiometric = await _appSecurity.canUseBiometrics();

    if (!hasPin && !hasBiometric) {
      _adminUnlocked = true;
      _adminUnlockedAt = DateTime.now();
      _showSnack(
        'Primeiro acesso administrativo liberado. Defina um PIN nas configurações para reforçar a segurança.',
      );
      return true;
    }

    if (hasBiometric) {
      final bioOk = await _appSecurity.authenticateAdmin();
      if (bioOk) {
        _adminUnlocked = true;
        _adminUnlockedAt = DateTime.now();
        return true;
      }
    }

    if (!hasPin) return false;

    final pinOk = await _validateAdminPinFlow();
    if (pinOk) {
      _adminUnlocked = true;
      _adminUnlockedAt = DateTime.now();
      return true;
    }

    return false;
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
              final whenIso = selectedDateTime?.toIso8601String() ?? '';
              try {
                Map<String, dynamic>? createdItem;
                bool synced = false;
                try {
                  final created = await _api.addReminder(text: text, when: whenIso);
                  if (created['ok'] == true && created['item'] is Map) {
                    createdItem = Map<String, dynamic>.from(created['item'] as Map);
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

                await _localDb.upsertReminder(createdItem);
                if (selectedDateTime != null) {
                  final id = DateTime.now().millisecondsSinceEpoch % 2147483647;
                  await _notifications.scheduleReminder(
                    id: id,
                    title: 'Lembrete da NOVA',
                    body: text,
                    when: selectedDateTime!,
                  );
                }
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

            return _PanelDialog(
              title: 'LEMBRETES',
              child: SizedBox(
                width: 640,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _NovaInput(
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

  Future<void> _openObservabilityDialog() async {
    final allowed = await _ensureAdminAccess();
    if (!mounted) return;
    if (!allowed) {
      _showSnack('Acesso administrativo negado.');
      return;
    }

    Map<String, dynamic> summary = {};
    List<Map<String, dynamic>> traces = [];
    String error = '';
    bool loading = false;

    Future<void> load() async {
      try {
        summary = await _api.getObservabilitySummary(window: 250);
        traces = await _api.getObservabilityTraces(limit: 120);
      } catch (_) {
        error =
            'Não foi possível carregar observabilidade no backend (verifique token/API).';
      }
    }

    await load();
    if (!mounted) return;

    await showDialog<void>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setLocalState) {
            Future<void> refresh() async {
              setLocalState(() {
                loading = true;
                error = '';
              });
              await load();
              if (!context.mounted) return;
              setLocalState(() => loading = false);
            }

            final total = summary['total']?.toString() ?? '0';
            final erroPct = summary['taxa_erro_pct']?.toString() ?? '0';
            final lat = summary['latencia_media_ms']?.toString() ?? '0';
            final alertsRaw = summary['alertas'];
            final alerts = (alertsRaw is List)
                ? alertsRaw.map((e) => e.toString()).toList()
                : <String>[];

            return _PanelDialog(
              title: 'OBSERVABILIDADE',
              child: SizedBox(
                width: 760,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (error.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Text(
                          error,
                          style: const TextStyle(color: Color(0xFFFF8A8A)),
                        ),
                      ),
                    Row(
                      children: [
                        Expanded(
                          child: Container(
                            padding: const EdgeInsets.all(10),
                            decoration: _boxDeco,
                            child: Text(
                              'Traces: $total',
                              style: const TextStyle(color: Color(0xFFD7F5FF)),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Container(
                            padding: const EdgeInsets.all(10),
                            decoration: _boxDeco,
                            child: Text(
                              'Erro: $erroPct%',
                              style: const TextStyle(color: Color(0xFFD7F5FF)),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Container(
                            padding: const EdgeInsets.all(10),
                            decoration: _boxDeco,
                            child: Text(
                              'Latência: ${lat}ms',
                              style: const TextStyle(color: Color(0xFFD7F5FF)),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: _boxDeco,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Alertas',
                            style: TextStyle(
                                color: Color(0xFFBDE8FF),
                                fontWeight: FontWeight.w700),
                          ),
                          const SizedBox(height: 6),
                          if (alerts.isEmpty)
                            const Text('Sem alertas no momento.',
                                style: TextStyle(color: Color(0xFF6DA7C8)))
                          else
                            ...alerts.map(
                              (a) => Padding(
                                padding: const EdgeInsets.only(bottom: 6),
                                child: Text(
                                  '- $a',
                                  style: const TextStyle(
                                      color: Color(0xFFD5F5FF), fontSize: 12),
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: _boxDeco,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Últimos traces',
                            style: TextStyle(
                                color: Color(0xFFBDE8FF),
                                fontWeight: FontWeight.w700),
                          ),
                          const SizedBox(height: 8),
                          ConstrainedBox(
                            constraints: const BoxConstraints(maxHeight: 260),
                            child: traces.isEmpty
                                ? const Text(
                                    'Sem traces ainda.',
                                    style: TextStyle(color: Color(0xFF6DA7C8)),
                                  )
                                : ListView.separated(
                                    shrinkWrap: true,
                                    itemCount: traces.length,
                                    separatorBuilder: (_, __) =>
                                        const SizedBox(height: 8),
                                    itemBuilder: (context, index) {
                                      final t = traces[traces.length - 1 - index];
                                      final ok = t['ok'] == true;
                                      final ev = t['evento']?.toString() ?? 'chat';
                                      final msg = t['mensagem_preview']?.toString() ?? '';
                                      final dur = t['duracao_ms']?.toString() ?? '-';
                                      return Container(
                                        padding: const EdgeInsets.all(8),
                                        decoration: BoxDecoration(
                                          color: const Color(0x4403182A),
                                          borderRadius: BorderRadius.circular(10),
                                          border: Border.all(
                                            color: ok
                                                ? const Color(0xFF0A4D74)
                                                : const Color(0xFF7B3030),
                                          ),
                                        ),
                                        child: Text(
                                          '[${ok ? "ok" : "erro"}] $ev · ${dur}ms\n$msg',
                                          style: const TextStyle(
                                            color: Color(0xFFD4F4FF),
                                            fontSize: 12,
                                            height: 1.35,
                                          ),
                                        ),
                                      );
                                    },
                                  ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        onPressed: loading ? null : refresh,
                        icon: loading
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.refresh),
                        label: Text(loading ? 'Atualizando...' : 'Atualizar'),
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

  Future<void> _openRagFeedbackDialog() async {
    final allowed = await _ensureAdminAccess();
    if (!mounted) return;
    if (!allowed) {
      _showSnack('Acesso administrativo negado.');
      return;
    }
    final queryController = TextEditingController();
    List<Map<String, dynamic>> items = [];
    String answer = '';
    String error = '';
    bool loading = false;

    await showDialog<void>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setLocalState) {
            Future<void> pesquisar() async {
              final q = queryController.text.trim();
              if (q.isEmpty) return;
              setLocalState(() {
                loading = true;
                error = '';
              });
              try {
                final out = await _api.ragQuery(q);
                final result = out['result'];
                if (result is! Map || result['ok'] != true) {
                  setLocalState(() {
                    error = 'RAG sem resultado para essa consulta.';
                    items = [];
                    answer = '';
                  });
                  return;
                }
                final arr = result['snippet_items'];
                final parsed = (arr is List)
                    ? arr
                        .whereType<Map>()
                        .map((e) => Map<String, dynamic>.from(e))
                        .toList()
                    : <Map<String, dynamic>>[];
                setLocalState(() {
                  items = parsed;
                  answer = result['answer']?.toString() ?? '';
                });
              } catch (_) {
                setLocalState(() {
                  error = 'Falha ao consultar RAG.';
                });
              } finally {
                if (context.mounted) {
                  setLocalState(() => loading = false);
                }
              }
            }

            Future<void> avaliar(String chunkId, int score) async {
              final q = queryController.text.trim();
              if (q.isEmpty || chunkId.isEmpty) return;
              try {
                await _api.ragFeedback(
                  query: q,
                  chunkId: chunkId,
                  score: score,
                );
                _showSnack(score > 0
                    ? 'Feedback positivo registrado.'
                    : 'Feedback negativo registrado.');
              } catch (_) {
                _showSnack('Falha ao registrar feedback RAG.');
              }
            }

            return _PanelDialog(
              title: 'RAG FEEDBACK',
              child: SizedBox(
                width: 760,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _NovaInput(
                      controller: queryController,
                      hintText: 'Pergunta para testar o RAG...',
                    ),
                    const SizedBox(height: 8),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        onPressed: loading ? null : pesquisar,
                        icon: loading
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.search),
                        label: Text(loading ? 'Pesquisando...' : 'Consultar RAG'),
                      ),
                    ),
                    if (error.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(error,
                          style: const TextStyle(color: Color(0xFFFF8A8A))),
                    ],
                    if (answer.isNotEmpty) ...[
                      const SizedBox(height: 10),
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: _boxDeco,
                        child: Text(
                          answer,
                          style: const TextStyle(
                              color: Color(0xFFD4F4FF), height: 1.35),
                        ),
                      ),
                    ],
                    const SizedBox(height: 10),
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxHeight: 300),
                      child: items.isEmpty
                          ? const Text(
                              'Sem trechos ainda. Faça uma consulta.',
                              style: TextStyle(color: Color(0xFF6DA7C8)),
                            )
                          : ListView.separated(
                              shrinkWrap: true,
                              itemCount: items.length,
                              separatorBuilder: (_, __) =>
                                  const SizedBox(height: 8),
                              itemBuilder: (context, index) {
                                final item = items[index];
                                final id = item['id']?.toString() ?? '';
                                final source = item['source']?.toString() ?? '-';
                                final text = item['text']?.toString() ?? '';
                                return Container(
                                  padding: const EdgeInsets.all(10),
                                  decoration: _boxDeco,
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        '$source • ${id.isEmpty ? "-" : id}',
                                        style: const TextStyle(
                                          color: Color(0xFF79B1CE),
                                          fontSize: 11,
                                        ),
                                      ),
                                      const SizedBox(height: 6),
                                      Text(
                                        text,
                                        style: const TextStyle(
                                          color: Color(0xFFD4F4FF),
                                          fontSize: 12,
                                          height: 1.35,
                                        ),
                                      ),
                                      const SizedBox(height: 6),
                                      Row(
                                        children: [
                                          OutlinedButton.icon(
                                            onPressed: id.isEmpty
                                                ? null
                                                : () => avaliar(id, 1),
                                            icon: const Icon(Icons.thumb_up_alt_outlined, size: 16),
                                            label: const Text('Relevante'),
                                          ),
                                          const SizedBox(width: 8),
                                          OutlinedButton.icon(
                                            onPressed: id.isEmpty
                                                ? null
                                                : () => avaliar(id, -1),
                                            icon: const Icon(Icons.thumb_down_alt_outlined, size: 16),
                                            label: const Text('Irrelevante'),
                                          ),
                                        ],
                                      )
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

    queryController.dispose();
  }

  Future<void> _openAgentControlDialog() async {
    final allowed = await _ensureAdminAccess();
    if (!mounted) return;
    if (!allowed) {
      _showSnack('Acesso administrativo negado.');
      return;
    }
    final objectiveController = TextEditingController();
    List<Map<String, dynamic>> plan = [];
    String agentMessage = '';
    bool loading = false;
    String error = '';

    await showDialog<void>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setLocalState) {
            Future<void> doPlan() async {
              final objective = objectiveController.text.trim();
              if (objective.isEmpty) return;
              setLocalState(() {
                loading = true;
                error = '';
              });
              try {
                final out = await _api.agentPlan(objective);
                final arr = out['plan'];
                final parsed = (arr is List)
                    ? arr
                        .whereType<Map>()
                        .map((e) => Map<String, dynamic>.from(e))
                        .toList()
                    : <Map<String, dynamic>>[];
                setLocalState(() => plan = parsed);
              } catch (_) {
                setLocalState(() => error = 'Falha ao planejar.');
              } finally {
                if (context.mounted) setLocalState(() => loading = false);
              }
            }

            Future<void> doExecute() async {
              final objective = objectiveController.text.trim();
              if (objective.isEmpty) return;
              setLocalState(() {
                loading = true;
                error = '';
              });
              try {
                final out = await _api.agentExecute(objective);
                agentMessage = out['message']?.toString() ?? '';
                final arr = out['plan'];
                final parsed = (arr is List)
                    ? arr
                        .whereType<Map>()
                        .map((e) => Map<String, dynamic>.from(e))
                        .toList()
                    : <Map<String, dynamic>>[];
                setLocalState(() => plan = parsed);
              } catch (_) {
                setLocalState(() => error = 'Falha ao executar agente.');
              } finally {
                if (context.mounted) setLocalState(() => loading = false);
              }
            }

            return _PanelDialog(
              title: 'AGENTE IA',
              child: SizedBox(
                width: 760,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _NovaInput(
                      controller: objectiveController,
                      hintText: 'Objetivo do agente...',
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: loading ? null : doPlan,
                            icon: const Icon(Icons.auto_graph),
                            label: const Text('Planejar'),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: FilledButton.icon(
                            onPressed: loading ? null : doExecute,
                            icon: loading
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  )
                                : const Icon(Icons.play_arrow),
                            label: Text(loading ? 'Executando...' : 'Executar'),
                          ),
                        ),
                      ],
                    ),
                    if (error.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(error,
                          style: const TextStyle(color: Color(0xFFFF8A8A))),
                    ],
                    if (agentMessage.isNotEmpty) ...[
                      const SizedBox(height: 10),
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: _boxDeco,
                        child: Text(
                          agentMessage,
                          style: const TextStyle(color: Color(0xFFD5F5FF)),
                        ),
                      ),
                    ],
                    const SizedBox(height: 10),
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxHeight: 260),
                      child: plan.isEmpty
                          ? const Text(
                              'Sem plano ainda.',
                              style: TextStyle(color: Color(0xFF6DA7C8)),
                            )
                          : ListView.separated(
                              shrinkWrap: true,
                              itemCount: plan.length,
                              separatorBuilder: (_, __) =>
                                  const SizedBox(height: 8),
                              itemBuilder: (context, index) {
                                final p = plan[index];
                                final act = p['action']?.toString() ?? '-';
                                final desc = p['description']?.toString() ?? '-';
                                final status = p['status']?.toString() ?? '';
                                return Container(
                                  padding: const EdgeInsets.all(10),
                                  decoration: _boxDeco,
                                  child: Text(
                                    '${index + 1}. $desc\nAção: $act${status.isEmpty ? '' : '\nStatus: $status'}',
                                    style: const TextStyle(
                                      color: Color(0xFFD4F4FF),
                                      fontSize: 12,
                                      height: 1.35,
                                    ),
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

    objectiveController.dispose();
  }

  Future<void> _openCompatibilityDialog() async {
    if (!mounted) return;
    final itens = PlatformCapabilities.matrixRich();
    await showDialog<void>(
      context: context,
      builder: (context) {
        return _PanelDialog(
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
                          _CapabilityBadge(status: item['status'] ?? 'parcial'),
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
      _chat.add(_ChatLine(fromUser: true, text: message));
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
        _chat.add(_ChatLine(fromUser: false, text: reply));
        _systemStatus = 'Resposta recebida.';
      });
      await _speak(reply);
      await _refreshAdminState();
      await _refreshMarketQuotes();
      await _loadReminders();
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _chat.add(
          const _ChatLine(
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
        return _PanelDialog(
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
              const _FieldLabel('GATILHO (o que o usuário diz)'),
              const SizedBox(height: 8),
              _NovaInput(
                  controller: triggerController,
                  hintText: 'Ex: qual seu nome?'),
              const SizedBox(height: 14),
              const _FieldLabel('RESPOSTA DA NOVA'),
              const SizedBox(height: 8),
              _NovaInput(
                controller: responseController,
                hintText: 'Ex: Meu nome é NOVA...',
                maxLines: 4,
              ),
              const SizedBox(height: 14),
              const _FieldLabel('CATEGORIA'),
              const SizedBox(height: 8),
              _NovaInput(controller: categoryController, hintText: 'geral'),
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
                  return _PanelDialog(
                    title: 'EDITAR ITEM',
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _NovaInput(
                            controller: triggerCtrl, hintText: 'Gatilho'),
                        const SizedBox(height: 10),
                        _NovaInput(
                            controller: responseCtrl,
                            hintText: 'Resposta',
                            maxLines: 3),
                        const SizedBox(height: 10),
                        _NovaInput(controller: catCtrl, hintText: 'Categoria'),
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

            return _PanelDialog(
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

            return _PanelDialog(
              title: 'GERENCIAR USUÁRIOS',
              child: SizedBox(
                width: 620,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: _NovaInput(
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
        _config['voice_profile']?.toString().trim().toLowerCase() ??
            'feminina';
    bool escutaAtiva = _config['escuta_ativa'] != false;
    bool telegramAtivo = _config['telegram_ativo'] == true;
    bool wakeContinuo = _config['continuous_wake'] != false;
    bool pushToTalkOnly = _config['push_to_talk_only'] != false;
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

            return _PanelDialog(
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
                          _NovaInput(
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
                          _NovaInput(
                              controller: telegramTokenController,
                              hintText: 'Bot Token'),
                          const SizedBox(height: 8),
                          _NovaInput(
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

  int get _learnedReplies => _knowledge.length;

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
          (label: 'Usuários', icon: Icons.people_outline, onTap: _openUsersDialog),
          (label: 'Ensinar', icon: Icons.school_outlined, onTap: _openTeachDialog),
          (label: 'Editar Base', icon: Icons.edit_note, onTap: _openKnowledgeDialog),
          (label: 'Lembretes', icon: Icons.alarm, onTap: _openRemindersDialog),
          (label: 'Agente IA', icon: Icons.smart_toy_outlined, onTap: _openAgentControlDialog),
          (label: 'Observabilidade', icon: Icons.monitor_heart_outlined, onTap: _openObservabilityDialog),
          (label: 'RAG Feedback', icon: Icons.thumb_up_alt_outlined, onTap: _openRagFeedbackDialog),
          (label: 'Auditoria', icon: Icons.security, onTap: _openSecurityAuditDialog),
          (label: 'Compatibilidade', icon: Icons.devices, onTap: _openCompatibilityDialog),
          (label: 'Configurações', icon: Icons.settings_outlined, onTap: _openConfigDialog),
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
                            leading: Icon(item.icon, color: const Color(0xFF6CD2FF)),
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
                        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: 2,
                          mainAxisSpacing: 10,
                          crossAxisSpacing: 10,
                          childAspectRatio: 2.8,
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
                              child: Text(item.label, maxLines: 1, overflow: TextOverflow.ellipsis),
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          const _GridBackground(),
          SafeArea(
            child: Column(
              children: [
                _TopBar(
                  onMenu: _openQuickMenu,
                ),
                Expanded(
                  child: Column(
                    children: [
                      Padding(
                        padding: const EdgeInsets.fromLTRB(8, 8, 8, 0),
                        child: _LocationPanel(
                          label: _locationLabel,
                          weather: _locationWeather,
                          loading: _loadingLocation,
                          onRefresh: _updateLocation,
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(8, 8, 8, 0),
                        child: _MarketPanel(quotes: _marketQuotes),
                      ),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(8, 8, 8, 0),
                        child: _MobileStatsStrip(
                          usersCount: _users.length,
                          messagesCount: _chat.length,
                          learnedCount: _learnedReplies,
                          onTeach: _openTeachDialog,
                        ),
                      ),
                      Expanded(
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(8, 8, 8, 0),
                          child: Align(
                            alignment: Alignment.topCenter,
                            child: ConstrainedBox(
                              constraints: const BoxConstraints(maxWidth: 980),
                              child: ListView.builder(
                                reverse: true,
                                itemCount: _chat.length,
                                itemBuilder: (context, index) {
                                  final item = _chat[_chat.length - 1 - index];
                                  return Align(
                                    alignment: item.fromUser
                                        ? Alignment.centerRight
                                        : Alignment.centerLeft,
                                    child: Container(
                                      margin: const EdgeInsets.only(bottom: 10),
                                      constraints:
                                          const BoxConstraints(maxWidth: 720),
                                      padding: const EdgeInsets.symmetric(
                                          horizontal: 12, vertical: 10),
                                      decoration: BoxDecoration(
                                        borderRadius: BorderRadius.circular(14),
                                        color: item.fromUser
                                            ? const Color(0xFF0A3752)
                                            : const Color(0xFF051D2E),
                                        border: Border.all(
                                          color: item.fromUser
                                              ? const Color(0xFF0AA7DE)
                                              : const Color(0xFF084A70),
                                        ),
                                      ),
                                      child: Text(
                                        item.text,
                                        style: const TextStyle(
                                          color: Color(0xFFCAEEFF),
                                          height: 1.35,
                                          fontSize: 14,
                                        ),
                                      ),
                                    ),
                                  );
                                },
                              ),
                            ),
                          ),
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(8, 8, 8, 8),
                        child: Align(
                          alignment: Alignment.center,
                          child: ConstrainedBox(
                            constraints: const BoxConstraints(maxWidth: 980),
                            child: Container(
                              padding:
                                  const EdgeInsets.symmetric(horizontal: 8),
                              height: 56,
                              decoration: BoxDecoration(
                                color: const Color(0xCC031A2A),
                                borderRadius: BorderRadius.circular(14),
                                border:
                                    Border.all(color: const Color(0xFF0C4D72)),
                              ),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: TextField(
                                      controller: _messageController,
                                      style: const TextStyle(
                                          color: Color(0xFF34C8FF)),
                                      cursorColor: const Color(0xFF34C8FF),
                                      decoration: const InputDecoration(
                                        border: InputBorder.none,
                                        hintText: 'Digite ou fale...',
                                        hintStyle:
                                            TextStyle(color: Color(0xFF567C95)),
                                      ),
                                      onSubmitted: (_) => _handleSendMessage(),
                                    ),
                                  ),
                                  IconButton(
                                    onPressed: _speechReady
                                        ? _toggleListening
                                        : _initSpeech,
                                    icon: Icon(
                                      _isListening ? Icons.mic : Icons.mic_none,
                                      color: _isListening
                                          ? const Color(0xFF00D9FF)
                                          : const Color(0xFF5FA6C8),
                                    ),
                                  ),
                                  IconButton(
                                    onPressed:
                                        _sending ? null : _handleSendMessage,
                                    icon: _sending
                                        ? const SizedBox(
                                            width: 18,
                                            height: 18,
                                            child: CircularProgressIndicator(
                                              strokeWidth: 2,
                                              color: Color(0xFF4CD7FF),
                                            ),
                                          )
                                        : const Icon(
                                            Icons.send_rounded,
                                            color: Color(0xFF3FCFFF),
                                          ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: Text(
                          _systemStatus,
                          style: const TextStyle(
                              color: Color(0xFF5B90AF), fontSize: 11),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({
    required this.onMenu,
  });

  final VoidCallback onMenu;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 560;
        final tiny = constraints.maxWidth < 420;
        final logoSize = compact ? 26.0 : 30.0;
        final titleSize = tiny ? 20.0 : (compact ? 24.0 : 32.0);
        final barHeight = compact ? 54.0 : 60.0;
        return Container(
          height: barHeight,
          padding: EdgeInsets.symmetric(horizontal: compact ? 8 : 12),
          decoration: BoxDecoration(
            color: const Color(0xCC02111D),
            border: Border(
              bottom: BorderSide(
                color: const Color(0xFF0B3D5F).withValues(alpha: 0.6),
              ),
            ),
          ),
          child: Row(
            children: [
              Container(
                width: logoSize,
                height: logoSize,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: const Color(0xFF0FA8DA)),
                  boxShadow: const [
                    BoxShadow(
                      color: Color(0x5510CEFF),
                      blurRadius: 8,
                      spreadRadius: 0.5,
                    ),
                  ],
                ),
                child: ClipOval(
                  child: Image.asset('assets/giphy3.gif', fit: BoxFit.cover),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.centerLeft,
                  child: Text(
                    'NOVA',
                    style: TextStyle(
                      color: const Color(0xFF21CCFF),
                      fontSize: titleSize,
                      letterSpacing: compact ? 1.0 : 1.8,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
              _TopAction(
                compact: tiny,
                label: 'Menu',
                icon: Icons.menu_rounded,
                onTap: onMenu,
              ),
            ],
          ),
        );
      },
    );
  }
}

class _TopAction extends StatelessWidget {
  const _TopAction({
    required this.label,
    required this.icon,
    required this.onTap,
    this.compact = false,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    if (compact) {
      return IconButton(
        onPressed: onTap,
        tooltip: label,
        icon: const Icon(Icons.menu_rounded, color: Color(0xFF77D8FF)),
        style: IconButton.styleFrom(
          side: const BorderSide(color: Color(0xFF0A446A)),
          backgroundColor: const Color(0x3303182A),
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: OutlinedButton.icon(
        onPressed: onTap,
        icon: Icon(icon, size: 18),
        label: Text(label),
        style: OutlinedButton.styleFrom(
          foregroundColor: const Color(0xFF77D8FF),
          side: const BorderSide(color: Color(0xFF0A446A)),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
      ),
    );
  }
}

class _LocationPanel extends StatelessWidget {
  const _LocationPanel({
    required this.label,
    required this.weather,
    required this.loading,
    required this.onRefresh,
  });

  final String label;
  final String weather;
  final bool loading;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0x8F02111D),
        border: Border.all(color: const Color(0xFF083D5E)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          const Icon(Icons.location_on_outlined, color: Color(0xFF74D8FF)),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFFD2F3FF),
                    fontWeight: FontWeight.w600,
                    fontSize: 12,
                  ),
                ),
                if (weather.trim().isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(
                    weather,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Color(0xFF79AFCB),
                      fontSize: 11,
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 8),
          SizedBox(
            height: 34,
            child: OutlinedButton.icon(
              onPressed: loading ? null : onRefresh,
              icon: loading
                  ? const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.my_location, size: 16),
              label: Text(loading ? 'Atualizando' : 'Localizar'),
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFF8BE5FF),
                side: const BorderSide(color: Color(0xFF0A446A)),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _MobileStatsStrip extends StatelessWidget {
  const _MobileStatsStrip({
    required this.usersCount,
    required this.messagesCount,
    required this.learnedCount,
    required this.onTeach,
  });

  final int usersCount;
  final int messagesCount;
  final int learnedCount;
  final VoidCallback onTeach;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 620;
        return Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: const Color(0x8F02111D),
            border: Border.all(color: const Color(0xFF083D5E)),
            borderRadius: BorderRadius.circular(12),
          ),
          child: compact
              ? Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: _StatTile(label: 'Msgs', value: '$messagesCount'),
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: _StatTile(label: 'Ensino', value: '$learnedCount'),
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: _StatTile(label: 'Users', value: '$usersCount'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton(
                        onPressed: onTeach,
                        child: const Text('Ensinar'),
                      ),
                    ),
                  ],
                )
              : Row(
                  children: [
                    Expanded(
                      child: _StatTile(label: 'Msgs', value: '$messagesCount'),
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: _StatTile(label: 'Ensino', value: '$learnedCount'),
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: _StatTile(label: 'Users', value: '$usersCount'),
                    ),
                    const SizedBox(width: 8),
                    FilledButton(
                      onPressed: onTeach,
                      child: const Text('Ensinar'),
                    ),
                  ],
                ),
        );
      },
    );
  }
}

class _StatTile extends StatelessWidget {
  const _StatTile({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 40,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFF0A4C74)),
        color: const Color(0x3A031E32),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 10),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: const TextStyle(color: Color(0xFF6DA7C8)),
            ),
          ),
          Text(
            value,
            style: const TextStyle(
                color: Color(0xFF2FE0FF), fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}

class _MarketPanel extends StatelessWidget {
  const _MarketPanel({required this.quotes});

  final Map<String, dynamic> quotes;

  String _fmt(dynamic v, {int dec = 2}) {
    if (v is num) return v.toStringAsFixed(dec);
    final n = num.tryParse(v?.toString() ?? '');
    if (n == null) return '--';
    return n.toStringAsFixed(dec);
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 520;
        final chips = [
          _QuoteChip(
              label: 'USD/BRL', value: _fmt(quotes['dolar_brl'], dec: 4)),
          _QuoteChip(label: 'BTC', value: _fmt(quotes['bitcoin_usd'])),
          _QuoteChip(label: 'EUR/BRL', value: _fmt(quotes['euro_brl'], dec: 4)),
          _QuoteChip(label: 'ETH', value: _fmt(quotes['ethereum_usd'])),
        ];

        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: const Color(0x55031D2F),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFF0A4A70)),
          ),
          child: compact
              ? Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Mercado',
                      style: TextStyle(
                        color: Color(0xFF59D8FF),
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: chips,
                    ),
                  ],
                )
              : SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      const Text(
                        'Mercado',
                        style: TextStyle(
                          color: Color(0xFF59D8FF),
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(width: 10),
                      ...[
                        chips[0],
                        const SizedBox(width: 8),
                        chips[2],
                        const SizedBox(width: 8),
                        chips[1],
                        const SizedBox(width: 8),
                        chips[3],
                      ],
                    ],
                  ),
                ),
        );
      },
    );
  }
}

class _QuoteChip extends StatelessWidget {
  const _QuoteChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(9),
        color: const Color(0x70021322),
        border: Border.all(color: const Color(0xFF095077)),
      ),
      child: Text(
        '$label: $value',
        style: const TextStyle(
          color: Color(0xFFAFE9FF),
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class _CapabilityBadge extends StatelessWidget {
  const _CapabilityBadge({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final s = status.toLowerCase().trim();
    late Color bg;
    late Color fg;
    late String label;

    if (s == 'completo') {
      bg = const Color(0x2638D27A);
      fg = const Color(0xFF8DFFBE);
      label = 'Completo';
    } else if (s == 'indisponivel') {
      bg = const Color(0x26D25A5A);
      fg = const Color(0xFFFF9D9D);
      label = 'Indisponível';
    } else {
      bg = const Color(0x26D2B85A);
      fg = const Color(0xFFFFE39E);
      label = 'Parcial';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: fg.withValues(alpha: 0.5)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: fg,
          fontSize: 11,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _AuditLevelBadge extends StatelessWidget {
  const _AuditLevelBadge({required this.level});

  final String level;

  @override
  Widget build(BuildContext context) {
    final l = level.toLowerCase();
    Color bg;
    Color fg;
    String label;

    if (l == 'bom') {
      bg = const Color(0x3323E79B);
      fg = const Color(0xFF26F0A2);
      label = 'BOM';
    } else if (l == 'critico') {
      bg = const Color(0x33FF4D4D);
      fg = const Color(0xFFFF7373);
      label = 'CRÍTICO';
    } else {
      bg = const Color(0x33FFD34D);
      fg = const Color(0xFFFFDF7A);
      label = 'ATENÇÃO';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: fg.withValues(alpha: 0.7)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: fg,
          fontWeight: FontWeight.w800,
          fontSize: 11,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}

class _AuditTimelineRow extends StatelessWidget {
  const _AuditTimelineRow({required this.item});

  final Map<String, dynamic> item;

  @override
  Widget build(BuildContext context) {
    final score = (item['score'] is num)
        ? (item['score'] as num).toInt()
        : int.tryParse(item['score']?.toString() ?? '0') ?? 0;
    final safeScore = score.clamp(0, 100);
    final when = item['audit_time']?.toString() ?? '-';
    final nivel = item['nivel']?.toString() ?? 'atencao';
    final achados = (item['achados_total'] is num)
        ? (item['achados_total'] as num).toInt()
        : int.tryParse(item['achados_total']?.toString() ?? '0') ?? 0;

    Color barColor;
    if (safeScore >= 85) {
      barColor = const Color(0xFF27E8A0);
    } else if (safeScore >= 65) {
      barColor = const Color(0xFFFFD36C);
    } else {
      barColor = const Color(0xFFFF6B6B);
    }

    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: const Color(0x4403182A),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFF084B74)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  when,
                  style: const TextStyle(
                    color: Color(0xFF84B5CF),
                    fontSize: 11,
                  ),
                ),
              ),
              Text(
                '$safeScore/100',
                style: const TextStyle(
                  color: Color(0xFFD8F5FF),
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              value: safeScore / 100.0,
              minHeight: 8,
              backgroundColor: const Color(0x55053A58),
              valueColor: AlwaysStoppedAnimation<Color>(barColor),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'nível: $nivel • achados: $achados',
            style: const TextStyle(
              color: Color(0xFF6FA4C3),
              fontSize: 11,
            ),
          ),
        ],
      ),
    );
  }
}

class _PanelDialog extends StatelessWidget {
  const _PanelDialog({
    required this.title,
    required this.child,
    this.actions = const [],
  });

  final String title;
  final Widget child;
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.sizeOf(context);
    final maxWidth = size.width < 420 ? size.width * 0.97 : size.width * 0.94;
    final targetWidth = maxWidth > 920 ? 920.0 : maxWidth;
    final targetHeight = size.height * 0.9;
    return Dialog(
      backgroundColor: Colors.transparent,
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxWidth: targetWidth,
          maxHeight: targetHeight,
        ),
        child: Container(
          decoration: BoxDecoration(
            color: const Color(0xE6031626),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0xFF0A4D74)),
            boxShadow: const [
              BoxShadow(
                color: Color(0x77000F1E),
                blurRadius: 28,
                spreadRadius: 1,
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 8, 10),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: const Color(0xFF00CEFF),
                          fontSize: size.width < 460 ? 18 : 24,
                          letterSpacing: 1.1,
                        ),
                      ),
                    ),
                    ...actions,
                    IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(Icons.close, color: Color(0xFF5DA3C6)),
                    ),
                  ],
                ),
              ),
              const Divider(height: 1, color: Color(0xFF0A3F60)),
              Flexible(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: child,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _FieldLabel extends StatelessWidget {
  const _FieldLabel(this.value);

  final String value;

  @override
  Widget build(BuildContext context) {
    return Text(
      value,
      style: const TextStyle(
        color: Color(0xFF00CCFF),
        fontSize: 17,
        letterSpacing: 0.8,
      ),
    );
  }
}

class _NovaInput extends StatelessWidget {
  const _NovaInput({
    required this.controller,
    required this.hintText,
    this.maxLines = 1,
  });

  final TextEditingController controller;
  final String hintText;
  final int maxLines;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      maxLines: maxLines,
      style: const TextStyle(color: Color(0xFFCBEFFF)),
      decoration: InputDecoration(
        hintText: hintText,
        hintStyle: const TextStyle(color: Color(0xFF537B95)),
        filled: true,
        fillColor: const Color(0x78031829),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: Color(0xFF084D76)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: Color(0xFF084D76)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: Color(0xFF0ED3FF), width: 1.2),
        ),
      ),
    );
  }
}

class _ChatLine {
  const _ChatLine({
    required this.fromUser,
    required this.text,
  });

  final bool fromUser;
  final String text;
}

class _GridBackground extends StatelessWidget {
  const _GridBackground();

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _GridPainter(),
      size: Size.infinite,
      child: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment.topCenter,
            radius: 1.2,
            colors: [
              Color(0xFF05233A),
              Color(0xFF020D1A),
              Color(0xFF000711),
            ],
          ),
        ),
      ),
    );
  }
}

class _GridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final gridPaint = Paint()
      ..color = const Color(0xFF0B3552).withValues(alpha: 0.35)
      ..strokeWidth = 1;

    const step = 32.0;
    for (double x = 0; x < size.width; x += step) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), gridPaint);
    }
    for (double y = 0; y < size.height; y += step) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
