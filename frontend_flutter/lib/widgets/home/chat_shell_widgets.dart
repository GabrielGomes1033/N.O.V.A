import 'package:flutter/material.dart';

class NovaChatLine {
  const NovaChatLine({
    required this.fromUser,
    required this.text,
  });

  final bool fromUser;
  final String text;
}

class NovaTopBar extends StatelessWidget {
  const NovaTopBar({
    super.key,
    required this.onOpenQuickMenu,
    required this.onOpenUsersDialog,
    required this.onPickQuickPhoto,
    this.compact = true,
    this.compressed = false,
  });

  final VoidCallback onOpenQuickMenu;
  final VoidCallback onOpenUsersDialog;
  final VoidCallback onPickQuickPhoto;
  final bool compact;
  final bool compressed;

  @override
  Widget build(BuildContext context) {
    final controlSize = compressed ? 44.0 : 48.0;
    final actionsWidth = compact ? (compressed ? 90.0 : 96.0) : 108.0;
    return Row(
      children: [
        Container(
          width: controlSize,
          height: controlSize,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Color(0xFF24282D),
                Color(0xFF1A1C20),
              ],
            ),
            border: Border.all(color: const Color(0xFF3D4248)),
          ),
          child: IconButton(
            onPressed: onOpenQuickMenu,
            icon: const Icon(Icons.menu_rounded, color: Color(0xFF9CA3AB)),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Container(
            height: controlSize,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(24),
              gradient: const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Color(0xFF182A34),
                  Color(0xFF1C252D),
                ],
              ),
              border: Border.all(color: const Color(0xFF31414C)),
              boxShadow: const [
                BoxShadow(
                  color: Color(0x6625D1FF),
                  blurRadius: 22,
                  spreadRadius: 0.6,
                ),
              ],
            ),
            child: const Center(
              child: Stack(
                alignment: Alignment.center,
                children: [
                  Opacity(
                    opacity: 0,
                    child: Text('NOVA'),
                  ),
                  Text(
                    'N . O . V . A',
                    style: TextStyle(
                      color: Color(0xFF14E6FF),
                      fontSize: 24 / 1.7,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 2.5,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(width: 10),
        Container(
          width: actionsWidth,
          height: controlSize,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Color(0xFF24282D),
                Color(0xFF1A1C20),
              ],
            ),
            border: Border.all(color: const Color(0xFF3D4248)),
          ),
          child: Row(
            children: [
              Expanded(
                child: IconButton(
                  onPressed: onOpenUsersDialog,
                  icon: const Icon(
                    Icons.person_add_alt_1_rounded,
                    color: Color(0xFFA3ABB3),
                    size: 20,
                  ),
                ),
              ),
              Expanded(
                child: IconButton(
                  onPressed: onPickQuickPhoto,
                  icon: const Icon(
                    Icons.camera_alt_outlined,
                    color: Color(0xFFA3ABB3),
                    size: 20,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class NovaChatTimeline extends StatelessWidget {
  const NovaChatTimeline({
    super.key,
    required this.chat,
    required this.compact,
    this.wide = false,
  });

  final List<NovaChatLine> chat;
  final bool compact;
  final bool wide;

  @override
  Widget build(BuildContext context) {
    final viewportWidth = MediaQuery.sizeOf(context).width;
    final bubbleMaxWidth =
        wide ? 560.0 : (compact ? viewportWidth * 0.8 : 460.0);
    final userBubbleMaxWidth =
        wide ? 520.0 : (compact ? viewportWidth * 0.76 : 440.0);
    final userLeftInset = wide ? 140.0 : 72.0;
    return ListView.builder(
      reverse: true,
      padding: const EdgeInsets.only(top: 2, bottom: 4),
      itemCount: chat.length,
      itemBuilder: (context, index) {
        final item = chat[chat.length - 1 - index];
        if (item.fromUser) {
          return Align(
            alignment: Alignment.centerRight,
            child: ConstrainedBox(
              constraints: BoxConstraints(maxWidth: userBubbleMaxWidth),
              child: Container(
                margin: EdgeInsets.only(bottom: 10, left: userLeftInset),
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(14),
                  color: const Color(0xFF182B3B),
                  border: Border.all(color: const Color(0xFF356487)),
                ),
                child: Text(
                  item.text,
                  style: const TextStyle(
                    color: Color(0xFFE8F7FF),
                    height: 1.34,
                    fontSize: 14,
                  ),
                ),
              ),
            ),
          );
        }
        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 38,
                height: 38,
                margin: const EdgeInsets.only(top: 4),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: const Color(0xFF1F8CB8)),
                  boxShadow: const [
                    BoxShadow(
                      color: Color(0x6612BFFF),
                      blurRadius: 14,
                      spreadRadius: 0.4,
                    ),
                  ],
                ),
                child: ClipOval(
                  child: Image.asset('assets/giphy3.gif', fit: BoxFit.cover),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Container(
                  constraints: BoxConstraints(
                    maxWidth: bubbleMaxWidth,
                  ),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 12,
                  ),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1A1E24),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: const Color(0xFF3D434C)),
                  ),
                  child: Text(
                    item.text,
                    style: const TextStyle(
                      color: Color(0xFFF3F8FF),
                      fontSize: 33 / 2.2,
                      height: 1.33,
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class NovaWorkspaceRail extends StatelessWidget {
  const NovaWorkspaceRail({
    super.key,
    required this.greeting,
    required this.systemStatus,
    required this.apiBaseUrl,
    required this.wakeWord,
    required this.voiceEnabled,
    required this.speechReady,
    required this.autonomyEnabled,
    required this.continuousWake,
    required this.examples,
    this.compressed = false,
  });

  final String greeting;
  final String systemStatus;
  final String apiBaseUrl;
  final String wakeWord;
  final bool voiceEnabled;
  final bool speechReady;
  final bool autonomyEnabled;
  final bool continuousWake;
  final List<String> examples;
  final bool compressed;

  @override
  Widget build(BuildContext context) {
    final gap = compressed ? 12.0 : 16.0;
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xCC0B1318),
            Color(0xCC101A21),
          ],
        ),
        border: Border.all(color: const Color(0xFF203847)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x3321D8FF),
            blurRadius: 36,
            spreadRadius: 0.2,
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(28),
        child: ListView(
          padding: EdgeInsets.all(compressed ? 18 : 22),
          children: [
            const Text(
              'NOVA ORBITAL',
              style: TextStyle(
                color: Color(0xFF6EDFFF),
                fontSize: 12,
                fontWeight: FontWeight.w700,
                letterSpacing: 1.8,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              greeting,
              style: const TextStyle(
                color: Color(0xFFF4FAFF),
                fontSize: 28,
                fontWeight: FontWeight.w700,
                height: 1.05,
              ),
            ),
            const SizedBox(height: 10),
            const Text(
              'A shell principal agora se abre melhor em telas amplas e mantém o fluxo do chat no centro da experiência.',
              style: TextStyle(
                color: Color(0xFFA5B8C6),
                fontSize: 14,
                height: 1.45,
              ),
            ),
            SizedBox(height: gap),
            _NovaRailCard(
              title: 'Status do Sistema',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    systemStatus,
                    style: const TextStyle(
                      color: Color(0xFFE9F6FF),
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _NovaSignalChip(
                        label: voiceEnabled ? 'Voz ativa' : 'Voz desligada',
                        active: voiceEnabled,
                      ),
                      _NovaSignalChip(
                        label:
                            speechReady ? 'Microfone pronto' : 'Microfone off',
                        active: speechReady,
                      ),
                      _NovaSignalChip(
                        label: autonomyEnabled
                            ? 'Autonomia ligada'
                            : 'Autonomia off',
                        active: autonomyEnabled,
                      ),
                      _NovaSignalChip(
                        label:
                            continuousWake ? 'Wake contínuo' : 'Push-to-talk',
                        active: continuousWake,
                      ),
                    ],
                  ),
                ],
              ),
            ),
            SizedBox(height: gap),
            _NovaRailCard(
              title: 'Conexão',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Endpoint da API',
                    style: TextStyle(
                      color: Color(0xFF87A7BA),
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    apiBaseUrl,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Color(0xFFF3F8FF),
                      fontSize: 14,
                      height: 1.35,
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Wake word',
                    style: TextStyle(
                      color: Color(0xFF87A7BA),
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    wakeWord,
                    style: const TextStyle(
                      color: Color(0xFF6EDFFF),
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
            SizedBox(height: gap),
            _NovaRailCard(
              title: 'Exemplos Naturais',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: examples
                    .map(
                      (example) => Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Padding(
                              padding: EdgeInsets.only(top: 4),
                              child: Icon(
                                Icons.subdirectory_arrow_right_rounded,
                                size: 16,
                                color: Color(0xFF4BCFFF),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                example,
                                style: const TextStyle(
                                  color: Color(0xFFD8EAF7),
                                  fontSize: 13.5,
                                  height: 1.4,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    )
                    .toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _NovaRailCard extends StatelessWidget {
  const _NovaRailCard({
    required this.title,
    required this.child,
  });

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        color: const Color(0xAA121D24),
        border: Border.all(color: const Color(0xFF233A48)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: Color(0xFF82B5CF),
              fontSize: 12,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.1,
            ),
          ),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }
}

class _NovaSignalChip extends StatelessWidget {
  const _NovaSignalChip({
    required this.label,
    required this.active,
  });

  final String label;
  final bool active;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: active ? const Color(0x1F2AE3FF) : const Color(0x14161C22),
        border: Border.all(
          color: active ? const Color(0xFF2CCFFF) : const Color(0xFF31424E),
        ),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: active ? const Color(0xFFE6FAFF) : const Color(0xFFA4B0B9),
          fontSize: 12.5,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class NovaComposer extends StatelessWidget {
  const NovaComposer({
    super.key,
    required this.messageController,
    required this.composerAttachmentName,
    required this.speechReady,
    required this.isListening,
    required this.sending,
    required this.onPickComposerAttachment,
    required this.onToggleListening,
    required this.onInitSpeech,
    required this.onSendMessage,
    this.compact = true,
    this.compressed = false,
  });

  final TextEditingController messageController;
  final String? composerAttachmentName;
  final bool speechReady;
  final bool isListening;
  final bool sending;
  final VoidCallback onPickComposerAttachment;
  final VoidCallback onToggleListening;
  final VoidCallback onInitSpeech;
  final VoidCallback onSendMessage;
  final bool compact;
  final bool compressed;

  @override
  Widget build(BuildContext context) {
    final composerHeight = compressed ? 54.0 : 58.0;
    final actionSize = compact ? (compressed ? 46.0 : 50.0) : 52.0;
    final inputFontSize = compact ? 15.0 : 16.0;
    return Container(
      height: composerHeight,
      padding: const EdgeInsets.fromLTRB(6, 4, 4, 4),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(29),
        gradient: const LinearGradient(
          begin: Alignment.centerLeft,
          end: Alignment.centerRight,
          colors: [
            Color(0xFF202226),
            Color(0xFF202226),
          ],
        ),
        border: Border.all(color: const Color(0xFF202226)),
      ),
      child: Row(
        children: [
          IconButton(
            onPressed: onPickComposerAttachment,
            icon: const Icon(
              Icons.add_rounded,
              color: Color(0xFFD3D8DE),
              size: 23,
            ),
          ),
          Expanded(
            child: Container(
              height: 28,
              decoration: BoxDecoration(
                color: const Color(0xFF202226),
                borderRadius: BorderRadius.circular(14),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Center(
                child: TextField(
                  controller: messageController,
                  style: TextStyle(
                    color: const Color(0xFF4E7A99),
                    fontSize: inputFontSize,
                  ),
                  cursorColor: const Color(0xFF5D8BAD),
                  decoration: InputDecoration(
                    filled: true,
                    fillColor: const Color(0xFF202226),
                    border: InputBorder.none,
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: BorderSide.none,
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: BorderSide.none,
                    ),
                    isCollapsed: true,
                    hintText: composerAttachmentName == null
                        ? 'Digite sua mensagem...'
                        : 'Arquivo: $composerAttachmentName',
                    hintStyle: const TextStyle(
                      color: Color(0xFF747A82),
                      fontSize: 15,
                    ),
                  ),
                  onSubmitted: (_) => onSendMessage(),
                ),
              ),
            ),
          ),
          IconButton(
            onPressed: speechReady ? onToggleListening : onInitSpeech,
            icon: Icon(isListening ? Icons.mic : Icons.mic_none),
            color:
                isListening ? const Color(0xFFEAF0F5) : const Color(0xFFC5CBD1),
          ),
          SizedBox(
            width: actionSize,
            height: actionSize,
            child: FilledButton(
              onPressed: sending ? null : onSendMessage,
              style: FilledButton.styleFrom(
                padding: EdgeInsets.zero,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(25),
                ),
                backgroundColor: const Color(0xFFE9EDF1),
                foregroundColor: const Color(0xFF131519),
              ),
              child: sending
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.1,
                        color: Color(0xFF1D232A),
                      ),
                    )
                  : const Icon(Icons.multitrack_audio_rounded, size: 21),
            ),
          ),
        ],
      ),
    );
  }
}

class NovaGridBackground extends StatelessWidget {
  const NovaGridBackground({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: RadialGradient(
          center: Alignment(0, -0.95),
          radius: 1.15,
          colors: [
            Color(0x330DC8F6),
            Color(0x22070E14),
            Color(0xFF020304),
          ],
        ),
      ),
    );
  }
}
