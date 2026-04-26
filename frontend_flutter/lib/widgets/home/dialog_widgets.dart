import 'package:flutter/material.dart';

class NovaCapabilityBadge extends StatelessWidget {
  const NovaCapabilityBadge({super.key, required this.status});

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

class NovaAuditLevelBadge extends StatelessWidget {
  const NovaAuditLevelBadge({super.key, required this.level});

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

class NovaAuditTimelineRow extends StatelessWidget {
  const NovaAuditTimelineRow({super.key, required this.item});

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

class NovaPanelDialog extends StatelessWidget {
  const NovaPanelDialog({
    super.key,
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

class NovaFieldLabel extends StatelessWidget {
  const NovaFieldLabel(this.value, {super.key});

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

class NovaInput extends StatelessWidget {
  const NovaInput({
    super.key,
    required this.controller,
    required this.hintText,
    this.maxLines = 1,
    this.obscureText = false,
  });

  final TextEditingController controller;
  final String hintText;
  final int maxLines;
  final bool obscureText;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      maxLines: maxLines,
      obscureText: obscureText,
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
