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
  });

  final VoidCallback onOpenQuickMenu;
  final VoidCallback onOpenUsersDialog;
  final VoidCallback onPickQuickPhoto;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 48,
          height: 48,
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
            height: 48,
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
          width: 96,
          height: 48,
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
  });

  final List<NovaChatLine> chat;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      reverse: true,
      padding: const EdgeInsets.only(top: 2, bottom: 4),
      itemCount: chat.length,
      itemBuilder: (context, index) {
        final item = chat[chat.length - 1 - index];
        if (item.fromUser) {
          return Align(
            alignment: Alignment.centerRight,
            child: Container(
              margin: const EdgeInsets.only(bottom: 10, left: 72),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
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
                    maxWidth: compact ? MediaQuery.sizeOf(context).width * 0.8 : 420,
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

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 58,
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
                  style: const TextStyle(
                    color: Color(0xFF4E7A99),
                    fontSize: 15,
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
            color: isListening
                ? const Color(0xFFEAF0F5)
                : const Color(0xFFC5CBD1),
          ),
          SizedBox(
            width: 50,
            height: 50,
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
