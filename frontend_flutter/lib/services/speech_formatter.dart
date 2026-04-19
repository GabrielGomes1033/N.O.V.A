class SpeechFormatter {
  static const List<String> _units = <String>[
    'zero',
    'um',
    'dois',
    'três',
    'quatro',
    'cinco',
    'seis',
    'sete',
    'oito',
    'nove',
  ];

  static const Map<int, String> _teens = <int, String>{
    10: 'dez',
    11: 'onze',
    12: 'doze',
    13: 'treze',
    14: 'quatorze',
    15: 'quinze',
    16: 'dezesseis',
    17: 'dezessete',
    18: 'dezoito',
    19: 'dezenove',
  };

  static const Map<int, String> _tens = <int, String>{
    20: 'vinte',
    30: 'trinta',
    40: 'quarenta',
    50: 'cinquenta',
    60: 'sessenta',
    70: 'setenta',
    80: 'oitenta',
    90: 'noventa',
  };

  static const Map<int, String> _hundreds = <int, String>{
    100: 'cem',
    200: 'duzentos',
    300: 'trezentos',
    400: 'quatrocentos',
    500: 'quinhentos',
    600: 'seiscentos',
    700: 'setecentos',
    800: 'oitocentos',
    900: 'novecentos',
  };

  static const Map<int, String> _months = <int, String>{
    1: 'janeiro',
    2: 'fevereiro',
    3: 'março',
    4: 'abril',
    5: 'maio',
    6: 'junho',
    7: 'julho',
    8: 'agosto',
    9: 'setembro',
    10: 'outubro',
    11: 'novembro',
    12: 'dezembro',
  };

  static String _join(List<String> parts) {
    final clean = parts.where((String p) => p.trim().isNotEmpty).toList();
    if (clean.isEmpty) return '';
    if (clean.length == 1) return clean.first;
    return '${clean.sublist(0, clean.length - 1).join(', ')} e ${clean.last}';
  }

  static String integerToWords(int number) {
    if (number == 0) return _units[0];
    if (number < 0) return 'menos ${integerToWords(number.abs())}';
    if (number < 10) return _units[number];
    if (number < 20) return _teens[number]!;
    if (number < 100) {
      final int tens = (number ~/ 10) * 10;
      final int remainder = number % 10;
      if (remainder == 0) return _tens[tens]!;
      return '${_tens[tens]} e ${integerToWords(remainder)}';
    }
    if (number < 1000) {
      if (number == 100) return _hundreds[100]!;
      final int hundreds = (number ~/ 100) * 100;
      final int remainder = number % 100;
      final String prefix = hundreds == 100 ? 'cento' : _hundreds[hundreds]!;
      if (remainder == 0) return prefix;
      return '$prefix e ${integerToWords(remainder)}';
    }

    const List<List<dynamic>> scales = <List<dynamic>>[
      <dynamic>[1000000000000, 'trilhão', 'trilhões'],
      <dynamic>[1000000000, 'bilhão', 'bilhões'],
      <dynamic>[1000000, 'milhão', 'milhões'],
      <dynamic>[1000, 'mil', 'mil'],
    ];

    int remaining = number;
    final List<String> parts = <String>[];
    for (final List<dynamic> scale in scales) {
      final int divisor = scale[0] as int;
      final int amount = remaining ~/ divisor;
      if (amount == 0) continue;
      remaining %= divisor;
      if (divisor == 1000) {
        parts.add(amount == 1 ? 'mil' : '${integerToWords(amount)} mil');
      } else {
        final String label =
            amount == 1 ? scale[1] as String : scale[2] as String;
        parts.add('${integerToWords(amount)} $label');
      }
    }
    if (remaining > 0) {
      parts.add(integerToWords(remaining));
    }
    return _join(parts);
  }

  static double? _parseFlexibleNumber(String raw) {
    var value = raw.trim();
    if (value.isEmpty) return null;
    value = value.replaceAll(' ', '');
    value = value.replaceAll(RegExp(r'[^0-9,.\-]'), '');
    if (value.isEmpty) return null;

    if (value.contains(',') && value.contains('.')) {
      final bool commaIsDecimal =
          value.lastIndexOf(',') > value.lastIndexOf('.');
      value = commaIsDecimal
          ? value.replaceAll('.', '').replaceAll(',', '.')
          : value.replaceAll(',', '');
    } else if (value.contains(',')) {
      value = RegExp(r',\d{1,4}$').hasMatch(value)
          ? value.replaceAll('.', '').replaceAll(',', '.')
          : value.replaceAll(',', '');
    } else if (value.contains('.') && !RegExp(r'\.\d{1,4}$').hasMatch(value)) {
      value = value.replaceAll('.', '');
    }
    return double.tryParse(value);
  }

  static String _decimalToWords(double value) {
    final String text =
        value.toStringAsFixed(value.truncateToDouble() == value ? 0 : 2);
    final List<String> parts = text.split('.');
    if (parts.length == 1) return integerToWords(int.parse(parts.first));
    final String decimal = parts[1].replaceAll(RegExp(r'0+$'), '');
    if (decimal.isEmpty) return integerToWords(int.parse(parts.first));
    final String fractional = decimal.startsWith('0')
        ? decimal
            .split('')
            .map((String ch) => integerToWords(int.parse(ch)))
            .join(' ')
        : integerToWords(int.parse(decimal));
    return '${integerToWords(int.parse(parts.first))} vírgula $fractional';
  }

  static String currencyToWords(String raw, String currency) {
    final double? value = _parseFlexibleNumber(raw);
    if (value == null) return raw;
    final double rounded = double.parse(value.toStringAsFixed(2));
    final int whole = rounded.truncate();
    final int cents = ((rounded - whole).abs() * 100).round();
    final Map<String, List<String>> labels = <String, List<String>>{
      'BRL': <String>['real', 'reais'],
      'USD': <String>['dólar', 'dólares'],
      'EUR': <String>['euro', 'euros'],
    };
    final List<String> unit =
        labels[currency] ?? <String>['unidade', 'unidades'];
    final List<String> parts = <String>[];
    if (whole != 0 || cents == 0) {
      parts.add(
          '${integerToWords(whole.abs())} ${whole.abs() == 1 ? unit.first : unit.last}');
    }
    if (cents > 0) {
      parts.add(
          '${integerToWords(cents)} ${cents == 1 ? 'centavo' : 'centavos'}');
    }
    final String base = _join(parts);
    return rounded < 0 ? 'menos $base' : base;
  }

  static String temperatureToWords(String raw) {
    final double? value = _parseFlexibleNumber(raw);
    if (value == null) return raw;
    final String base = value.truncateToDouble() == value
        ? integerToWords(value.toInt())
        : _decimalToWords(value);
    return '$base graus';
  }

  static String percentToWords(String raw) {
    final double? value = _parseFlexibleNumber(raw);
    if (value == null) return raw;
    final String base = value.truncateToDouble() == value
        ? integerToWords(value.toInt())
        : _decimalToWords(value);
    return '$base por cento';
  }

  static String timeToWords(String raw) {
    final RegExpMatch? match =
        RegExp(r'^(\d{1,2}):(\d{2})(?::\d{2})?$').firstMatch(raw.trim());
    if (match == null) return raw;
    final int hour = int.parse(match.group(1)!);
    final int minute = int.parse(match.group(2)!);
    if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return raw;

    final String period;
    if (hour < 6) {
      period = 'da madrugada';
    } else if (hour < 12) {
      period = 'da manhã';
    } else if (hour < 19) {
      period = 'da tarde';
    } else {
      period = 'da noite';
    }

    final String base;
    if (hour == 0) {
      base = 'meia-noite';
    } else if (hour == 12) {
      base = 'meio-dia';
    } else {
      base = integerToWords(hour % 12 == 0 ? 12 : hour % 12);
    }

    if (minute == 0) {
      return base == 'meia-noite' || base == 'meio-dia'
          ? '$base em ponto'
          : '$base em ponto $period';
    }
    if (minute == 30) {
      return base == 'meia-noite' || base == 'meio-dia'
          ? '$base e meia'
          : '$base e meia $period';
    }
    final String minuteText = integerToWords(minute);
    return base == 'meia-noite' || base == 'meio-dia'
        ? '$base e $minuteText'
        : '$base e $minuteText $period';
  }

  static String dateToWords(String raw) {
    final String text = raw.trim();
    DateTime? dt;
    if (RegExp(r'^\d{1,2}/\d{1,2}/\d{2,4}$').hasMatch(text)) {
      final List<String> parts = text.split('/');
      final int day = int.parse(parts[0]);
      final int month = int.parse(parts[1]);
      final int year = parts[2].length == 2
          ? int.parse('20${parts[2]}')
          : int.parse(parts[2]);
      dt = DateTime(year, month, day);
    } else if (RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(text)) {
      dt = DateTime.tryParse(text);
    }
    if (dt == null) return raw;
    final String dayText = dt.day == 1 ? 'primeiro' : integerToWords(dt.day);
    final String monthText = _months[dt.month] ?? dt.month.toString();
    final String yearText = integerToWords(dt.year);
    return '$dayText de $monthText de $yearText';
  }

  static String timestampToWords(String raw) {
    final DateTime? dt = DateTime.tryParse(raw.trim());
    if (dt == null) return raw;
    return '${dateToWords(dt.toIso8601String().substring(0, 10))}, ${timeToWords('${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}')}';
  }

  static String prepareForSpeech(String text) {
    var output = text.trim();
    if (output.isEmpty) return output;

    output = output.replaceAll(RegExp(r'https?://\S+'), ' ');
    output = output.replaceAll('\n', '. ');
    output = output.replaceAll(RegExp(r'[_*`#]'), ' ');
    output = output.replaceAll('N.O.V.A', 'NOVA');

    output = output.replaceAllMapped(
      RegExp(
          r'\b(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}(?::\d{2})?(?:Z|[+\-]\d{2}:\d{2})?)\b'),
      (Match m) => timestampToWords(m.group(1)!),
    );
    output = output.replaceAllMapped(
      RegExp(r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b'),
      (Match m) => dateToWords(m.group(1)!),
    );
    output = output.replaceAllMapped(
      RegExp(r'\b(\d{4}-\d{2}-\d{2})\b'),
      (Match m) => dateToWords(m.group(1)!),
    );
    output = output.replaceAllMapped(
      RegExp(r'\b(\d{1,2}:\d{2}(?::\d{2})?)\b'),
      (Match m) => timeToWords(m.group(1)!),
    );

    final List<Map<String, String>> currencies = <Map<String, String>>[
      <String, String>{
        'pattern': r'R\$\s*([0-9]+(?:[.,][0-9]+)*)',
        'code': 'BRL'
      },
      <String, String>{
        'pattern': r'US\$\s*([0-9]+(?:[.,][0-9]+)*)',
        'code': 'USD'
      },
      <String, String>{
        'pattern': r'€\s*([0-9]+(?:[.,][0-9]+)*)',
        'code': 'EUR'
      },
    ];
    for (final Map<String, String> item in currencies) {
      output = output.replaceAllMapped(
        RegExp(item['pattern']!),
        (Match m) => currencyToWords(m.group(1)!, item['code']!),
      );
    }

    output = output.replaceAllMapped(
      RegExp(r'(-?\d+(?:[.,]\d+)?)\s*°\s*C', caseSensitive: false),
      (Match m) => temperatureToWords(m.group(1)!),
    );
    output = output.replaceAllMapped(
      RegExp(r'(-?\d+(?:[.,]\d+)?)\s*%'),
      (Match m) => percentToWords(m.group(1)!),
    );
    output = output.replaceAll(':', ', ');
    output = output.replaceAll(';', ', ');
    output = output.replaceAll(RegExp(r'\s+'), ' ').trim();
    return output;
  }
}
