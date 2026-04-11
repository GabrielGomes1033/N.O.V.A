import 'package:flutter/material.dart';

import 'screens/home_page.dart';
import 'theme/app_theme.dart';

// Widget raiz do aplicativo.
// Ele configura tema, título e rota inicial.
class NovaFrontendApp extends StatelessWidget {
  const NovaFrontendApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'NOVA Frontend',
      theme: AppTheme.lightTheme,
      home: const HomePage(),
    );
  }
}
