import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:speech_to_text/speech_to_text.dart';

import '../services/chat_api.dart';

// Esta tela e a "home" inicial do app.
// Ela mostra um cabecalho, alguns cards e um campo de mensagem.
class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final TextEditingController _messageController = TextEditingController();
  final SpeechToText _speech = SpeechToText();
  final FlutterTts _tts = FlutterTts();
  final ChatApiService _api = ChatApiService();

  final List<_ChatLine> _chat = [];
  String _systemStatus = 'Digite algo...';
  bool _speechReady = false;
  bool _isListening = false;
  bool _executedFromVoice = false;
  bool _sending = false;
  bool _ttsEnabled = true;
  Map<String, dynamic> _localMemoryBackup = {};
  String _backupUpdatedAt = '';

  static const _kBackupMemory = 'nova_backup_memory_v1';
  static const _kBackupUpdatedAt = 'nova_backup_updated_at_v1';

  @override
  void initState() {
    super.initState();
    _chat.add(
      _ChatLine(
        fromUser: false,
        text: 'Conectando com a NOVA em ${_api.baseUrl} ...',
      ),
    );
    _loadLocalBackup();
    _initTts();
    _initSpeech();
  }

  @override
  void dispose() {
    _tts.stop();
    _messageController.dispose();
    super.dispose();
  }

  Future<void> _initTts() async {
    await _tts.awaitSpeakCompletion(true);
    await _tts.setLanguage('pt-BR');
    await _tts.setSpeechRate(0.48);
    await _tts.setPitch(0.94);
    await _tts.setVolume(1.0);
    await _selectBestVoice();
  }

  Future<void> _loadLocalBackup() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_kBackupMemory);
    final updatedAt = prefs.getString(_kBackupUpdatedAt) ?? '';
    Map<String, dynamic> data = {};
    if (raw != null && raw.isNotEmpty) {
      try {
        final json = jsonDecode(raw);
        if (json is Map<String, dynamic>) {
          data = json;
        }
      } catch (_) {
        data = {};
      }
    }
    if (!mounted) return;
    setState(() {
      _localMemoryBackup = data;
      _backupUpdatedAt = updatedAt;
    });
  }

  Future<void> _saveLocalBackup(Map<String, dynamic> backup) async {
    final prefs = await SharedPreferences.getInstance();
    final now = DateTime.now().toIso8601String();
    await prefs.setString(_kBackupMemory, jsonEncode(backup));
    await prefs.setString(_kBackupUpdatedAt, now);
    if (!mounted) return;
    setState(() {
      _localMemoryBackup = backup;
      _backupUpdatedAt = now;
    });
  }

  Future<String> _syncBackupFromCloud() async {
    final backup = await _api.exportBackup();
    await _saveLocalBackup(backup);
    return 'Backup local sincronizado com sucesso.';
  }

  Future<String> _restoreBackupToCloud() async {
    if (_localMemoryBackup.isEmpty) {
      return 'Nenhum backup local encontrado para restaurar.';
    }
    await _api.restoreBackup(_localMemoryBackup);
    return 'Backup local restaurado na nuvem com sucesso.';
  }

  String _backupStatusText() {
    final hasMemory = (_localMemoryBackup['memory'] is Map);
    return 'Backup local: ${hasMemory ? "disponível" : "vazio"}\n'
        'Última atualização: ${_backupUpdatedAt.isEmpty ? "nunca" : _backupUpdatedAt}';
  }

  Future<void> _selectBestVoice() async {
    try {
      final voices = await _tts.getVoices;
      if (voices is! List) return;

      Map<String, dynamic>? best;
      for (final item in voices) {
        if (item is! Map) continue;
        final voice = Map<String, dynamic>.from(item);
        final locale = (voice['locale'] ?? voice['language'] ?? '').toString().toLowerCase();
        final name = (voice['name'] ?? '').toString().toLowerCase();
        if (!locale.contains('pt-br') && !locale.contains('pt_br')) continue;
        if (name.contains('female') ||
            name.contains('francisca') ||
            name.contains('maria') ||
            name.contains('helena') ||
            name.contains('brasil')) {
          best = voice;
          break;
        }
        best ??= voice;
      }

      if (best != null) {
        await _tts.setVoice(best.cast<String, String>());
      }
    } catch (_) {
      // Mantém a voz padrão do dispositivo.
    }
  }

  String _naturalizeSpeechText(String text) {
    var t = text.trim();
    if (t.isEmpty) return t;

    t = t.replaceAll(RegExp(r'https?://\S+'), ' ');
    t = t.replaceAll('\n', '. ');
    t = t.replaceAll(RegExp(r'[_*`#]'), ' ');
    t = t.replaceAll('%', ' por cento');
    t = t.replaceAll(RegExp(r'\s+'), ' ').trim();
    t = t.replaceAll('N.O.V.A', 'NOVA');
    return t;
  }

  List<String> _splitSpeechChunks(String text, {int maxChars = 220}) {
    if (text.length <= maxChars) return [text];
    final sentences = text.split(RegExp(r'(?<=[.!?])\s+'));
    final chunks = <String>[];
    var buffer = '';
    for (final s in sentences) {
      final part = s.trim();
      if (part.isEmpty) continue;
      if ((buffer.length + part.length + 1) <= maxChars) {
        buffer = buffer.isEmpty ? part : '$buffer $part';
      } else {
        if (buffer.isNotEmpty) chunks.add(buffer);
        buffer = part;
      }
    }
    if (buffer.isNotEmpty) chunks.add(buffer);
    return chunks.isEmpty ? [text] : chunks;
  }

  Future<void> _speak(String text) async {
    if (!_ttsEnabled) return;
    final clean = _naturalizeSpeechText(text);
    if (clean.isEmpty) return;
    await _tts.stop();
    final chunks = _splitSpeechChunks(clean);
    for (final chunk in chunks) {
      await _tts.speak(chunk);
      await Future<void>.delayed(const Duration(milliseconds: 120));
    }
  }

  Future<void> _handleSendMessage() async {
    final message = _messageController.text.trim();
    if (message.isEmpty) return;
    await _executeCommand(message, fromVoice: false);
  }

  Future<void> _initSpeech() async {
    final available = await _speech.initialize(
      onStatus: (status) {
        if (!mounted) return;
        if (status == 'done' || status == 'notListening') {
          setState(() => _isListening = false);
        }
      },
      onError: (error) {
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
      _systemStatus = available
          ? 'Digite algo...'
          : 'Microfone indisponivel neste dispositivo.';
    });
  }

  Future<void> _toggleListening() async {
    if (!_speechReady) {
      await _initSpeech();
      if (!_speechReady) return;
    }

    if (_isListening) {
      await _speech.stop();
      if (!mounted) return;
      setState(() {
        _isListening = false;
        _systemStatus = 'Escuta pausada.';
      });
      return;
    }

    setState(() {
      _isListening = true;
      _executedFromVoice = false;
      _systemStatus = 'Escutando comando de voz...';
    });

    await _speech.listen(
      localeId: 'pt_BR',
      partialResults: true,
      cancelOnError: true,
      listenFor: const Duration(seconds: 12),
      pauseFor: const Duration(seconds: 3),
      onResult: (result) {
        if (!mounted) return;
        final words = result.recognizedWords.trim();

        setState(() {
          _messageController.text = words;
          _messageController.selection = TextSelection.fromPosition(
            TextPosition(offset: _messageController.text.length),
          );
        });

        if (result.finalResult && words.isNotEmpty && !_executedFromVoice) {
          _executedFromVoice = true;
          _handleWakeWordVoice(words);
        }
      },
    );
  }

  Future<void> _handleWakeWordVoice(String words) async {
    final cleaned = words.trim();
    if (cleaned.isEmpty) return;

    final lower = cleaned.toLowerCase();
    if (!RegExp(r'\bnova\b').hasMatch(lower)) {
      if (!mounted) return;
      setState(() {
        _systemStatus = 'Diga "NOVA" para ativar o comando de voz.';
      });
      return;
    }

    // Remove apenas a primeira ocorrência de "nova" para extrair o comando.
    final command = cleaned.replaceFirst(RegExp(r'\bnova\b[:,]?\s*', caseSensitive: false), '').trim();
    if (command.isEmpty) {
      const ack = 'Sim senhor, o que precisa?';
      if (!mounted) return;
      setState(() {
        _chat.add(const _ChatLine(fromUser: false, text: ack));
        _systemStatus = 'Wake word detectada.';
      });
      await _speak(ack);
      return;
    }

    await _executeCommand(command, fromVoice: true);
  }

  Future<void> _executeCommand(String rawMessage, {required bool fromVoice}) async {
    final message = rawMessage.trim();
    if (message.isEmpty) return;

    final normalized = _normalizeLocalCommand(message);

    if (normalized == '/limpar') {
      setState(() {
        _chat.clear();
        _messageController.clear();
        _systemStatus = 'Digite algo...';
      });
      return;
    }

    if (normalized == '/ouvir') {
      await _toggleListening();
      return;
    }

    if (normalized == '/parar') {
      await _speech.stop();
      setState(() {
        _isListening = false;
        _systemStatus = 'Escuta encerrada por comando.';
      });
      return;
    }

    setState(() {
      _chat.add(_ChatLine(fromUser: true, text: message));
      _messageController.clear();
      _systemStatus = fromVoice ? 'Comando de voz enviado.' : 'Comando enviado.';
      _sending = true;
    });

    try {
      String reply;
      if (normalized == '/status') {
        reply = 'Status local OK. Microfone: ${_speechReady ? "ativo" : "inativo"}.\nAPI: ${_api.baseUrl}';
      } else if (normalized == '/backup status') {
        reply = _backupStatusText();
      } else if (normalized == '/backup ver') {
        if (_localMemoryBackup.isEmpty) {
          reply = 'Backup local vazio.';
        } else {
          reply = 'Backup local:\n${const JsonEncoder.withIndent('  ').convert(_localMemoryBackup)}';
        }
      } else if (normalized == '/backup sincronizar') {
        reply = await _syncBackupFromCloud();
      } else if (normalized == '/backup restaurar') {
        reply = await _restoreBackupToCloud();
      } else if (normalized == '/voz on' || normalized == '/voz ligar' || normalized == '/voz ativar') {
        _ttsEnabled = true;
        reply = 'Voz local ativada no celular.';
      } else if (normalized == '/voz off' || normalized == '/voz desligar' || normalized == '/voz desativar') {
        _ttsEnabled = false;
        await _tts.stop();
        reply = 'Voz local desativada no celular.';
      } else if (normalized == '/comando' || normalized == '/comandos') {
        reply = 'Comandos locais:\n'
            '/comando\n'
            '/ouvir\n'
            '/parar\n'
            '/status\n'
            '/voz on\n'
            '/voz off\n'
            '/backup status\n'
            '/backup sincronizar\n'
            '/backup restaurar\n'
            '/backup ver\n'
            '/limpar\n\n'
            'Demais mensagens vão para o backend da NOVA.';
      } else {
        reply = await _api.sendMessage(message);
        // Mantém um espelho local de memória após conversas normais.
        try {
          await _syncBackupFromCloud();
        } catch (_) {
          // Se falhar backup, não interrompe a conversa.
        }
      }

      if (!mounted) return;
      setState(() {
        _chat.add(_ChatLine(fromUser: false, text: reply));
        _systemStatus = 'Resposta recebida.';
      });
      await _speak(reply);
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _chat.add(
          const _ChatLine(
            fromUser: false,
            text: 'Falha ao conectar com a API da NOVA. Verifique IP/porta e se o servidor está ligado.',
          ),
        );
        _systemStatus = 'Erro de conexão com backend.';
      });
    } finally {
      if (!mounted) return;
      setState(() => _sending = false);
    }
  }

  String _normalizeLocalCommand(String input) {
    var text = input.toLowerCase().trim();
    text = text.replaceAll(RegExp(r'\s+'), ' ');
    text = text.replaceFirst(RegExp(r'^nova[,:]?\s+'), '');

    // Aceita forma falada de barra, ex: "barra voz on".
    if (text.startsWith('barra ')) {
      text = '/${text.substring(6).trim()}';
    }

    // Alias locais com linguagem natural.
    if (RegExp(r'^(lig(ar|ue)|ativ(ar|e)).*(comando )?de voz').hasMatch(text) ||
        RegExp(r'^voz (on|ligar|ativar)$').hasMatch(text) ||
        text == '/nova voz on') {
      return '/voz on';
    }

    if (RegExp(r'^(deslig(ar|ue)|desativ(ar|e)).*(comando )?de voz').hasMatch(text) ||
        RegExp(r'^voz (off|desligar|desativar)$').hasMatch(text) ||
        text == '/nova voz off') {
      return '/voz off';
    }

    if (RegExp(r'^(ouvir|escutar|iniciar escuta|iniciar voz)$').hasMatch(text)) {
      return '/ouvir';
    }

    if (RegExp(r'^(parar|parar escuta|parar voz)$').hasMatch(text)) {
      return '/parar';
    }

    return text;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            children: [
              const SizedBox(height: 30),
              const Text(
                'N.O.V.A',
                style: TextStyle(
                  color: Color(0xFF2FB5FF),
                  fontSize: 42,
                  letterSpacing: 3,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const Spacer(),
              _NovaOrb(
                isListening: _isListening,
                onTap: () {
                  if (_speechReady) {
                    _toggleListening();
                  } else {
                    _initSpeech();
                  }
                },
              ),
              const SizedBox(height: 24),
              Expanded(
                child: Align(
                  alignment: Alignment.topCenter,
                  child: ListView.builder(
                    reverse: true,
                    itemCount: _chat.length,
                    itemBuilder: (context, index) {
                      final item = _chat[_chat.length - 1 - index];
                      return Align(
                        alignment: item.fromUser ? Alignment.centerRight : Alignment.centerLeft,
                        child: Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                          constraints: const BoxConstraints(maxWidth: 320),
                          decoration: BoxDecoration(
                            color: item.fromUser ? const Color(0xFF2A89BE) : const Color(0xFF12293A),
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: Text(
                            item.text,
                            style: const TextStyle(color: Colors.white, fontSize: 13),
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ),
              Container(
                height: 56,
                padding: const EdgeInsets.symmetric(horizontal: 10),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(28),
                ),
                child: Row(
                  children: [
                    const SizedBox(width: 14),
                    Expanded(
                      child: TextField(
                        controller: _messageController,
                        style: const TextStyle(
                          color: Colors.black87,
                          fontSize: 15,
                        ),
                        decoration: InputDecoration(
                          border: InputBorder.none,
                          hintText: _systemStatus,
                          hintStyle: const TextStyle(
                            color: Colors.black54,
                            letterSpacing: 0.2,
                          ),
                        ),
                        onSubmitted: (_) => _handleSendMessage(),
                      ),
                    ),
                    Container(
                      width: 42,
                      height: 42,
                      decoration: const BoxDecoration(
                        color: Color(0xFF4AB6F5),
                        shape: BoxShape.circle,
                      ),
                      child: IconButton(
                        iconSize: 24,
                        padding: EdgeInsets.zero,
                        onPressed: _sending ? null : _handleSendMessage,
                        icon: _sending
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Icon(
                                Icons.arrow_upward_rounded,
                                color: Colors.white,
                              ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 50),
              Text(
                _systemStatus,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: Color(0xFF6CC9FF),
                  fontSize: 12,
                ),
              ),
              const SizedBox(height: 12),
            ],
          ),
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

class _NovaOrb extends StatelessWidget {
  final bool isListening;
  final VoidCallback onTap;

  const _NovaOrb({
    required this.isListening,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: SizedBox(
        width: 170,
        height: 170,
        child: Stack(
          alignment: Alignment.center,
          children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 250),
              width: isListening ? 150 : 138,
              height: isListening ? 150 : 138,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: isListening
                        ? const Color(0xAA2FB5FF)
                        : const Color(0x552FB5FF),
                    blurRadius: isListening ? 26 : 18,
                    spreadRadius: isListening ? 4 : 1,
                  ),
                ],
              ),
            ),
            ClipOval(
              child: SizedBox(
                width: 128,
                height: 128,
                child: Image.asset(
                  'assets/giphy3.gif',
                  fit: BoxFit.cover,
                ),
              ),
            ),
            Container(
              width: 132,
              height: 132,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: isListening
                      ? const Color(0xFF7CD7FF)
                      : const Color(0x669BDFFF),
                  width: isListening ? 2 : 1,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
