import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

// Centraliza as definicoes visuais do app.
// Quando voce quiser trocar cores/estilo global, altere aqui.
class AppTheme {
  static const Color primaryColor = Color(0xFF2FB5FF);
  static const Color secondaryColor = Color(0xFF1C8FD1);
  static const Color backgroundColor = Color(0xFF000000);
  static const Color surfaceColor = Color(0xFFFFFFFF);

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primaryColor,
        primary: primaryColor,
        secondary: secondaryColor,
        surface: surfaceColor,
        brightness: Brightness.dark,
      ),
      scaffoldBackgroundColor: backgroundColor,
      appBarTheme: const AppBarTheme(
        centerTitle: false,
        elevation: 0,
        backgroundColor: Colors.transparent,
        foregroundColor: Colors.white,
      ),
      fontFamily: GoogleFonts.ibmPlexSans().fontFamily,
      cardTheme: CardThemeData(
        elevation: 0,
        color: surfaceColor,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
      ),
      textTheme: const TextTheme(
        headlineSmall: TextStyle(
          color: Color(0xFF2FB5FF),
          fontWeight: FontWeight.w700,
          letterSpacing: 1.2,
        ),
        bodyMedium: TextStyle(
          color: Color(0xFFB8DFFF),
        ),
        titleMedium: TextStyle(
          color: Color(0xFFDFF2FF),
          fontWeight: FontWeight.w600,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: primaryColor, width: 1.4),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: primaryColor,
          foregroundColor: Colors.white,
          textStyle: const TextStyle(fontWeight: FontWeight.w600),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
    );
  }
}
