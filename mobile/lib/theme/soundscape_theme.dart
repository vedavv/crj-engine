import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Cosmic sacred theme matching the web UI.
class SoundScapeTheme {
  static const deepSacred = Color(0xFF0A0612);
  static const twilight = Color(0xFF1A0F2E);
  static const amberGlow = Color(0xFFD4A854);
  static const warmGold = Color(0xFFC5943A);
  static const sacredSaffron = Color(0xFFE8A031);
  static const flameAccent = Color(0xFFE87831);
  static const lotusPink = Color(0xFFC4607A);
  static const skyBlue = Color(0xFF4A8FB8);
  static const paleGold = Color(0xFFF5E6C8);
  static const mutedCream = Color(0xFFE8DCC8);
  static const textLight = Color(0xFFE8E0D4);
  static const textMuted = Color(0xFF9A8E7E);
  static const cardBg = Color(0xFF120C20);
  static const cardBorder = Color(0x26D4A854);

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: deepSacred,
      colorScheme: const ColorScheme.dark(
        primary: amberGlow,
        onPrimary: deepSacred,
        secondary: sacredSaffron,
        surface: cardBg,
        onSurface: textLight,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: deepSacred,
        elevation: 0,
        centerTitle: true,
        titleTextStyle: GoogleFonts.cinzel(
          fontSize: 14,
          letterSpacing: 3,
          color: amberGlow,
          fontWeight: FontWeight.w500,
        ),
        iconTheme: const IconThemeData(color: amberGlow),
      ),
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: deepSacred,
        selectedItemColor: amberGlow,
        unselectedItemColor: textMuted,
        selectedLabelStyle: GoogleFonts.cinzel(fontSize: 10, letterSpacing: 1.5),
        unselectedLabelStyle: GoogleFonts.cinzel(fontSize: 10, letterSpacing: 1),
        type: BottomNavigationBarType.fixed,
      ),
      cardTheme: CardThemeData(
        color: cardBg,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: const BorderSide(color: cardBorder),
        ),
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      ),
      textTheme: TextTheme(
        headlineLarge: GoogleFonts.cinzel(
          fontSize: 20, letterSpacing: 4, color: amberGlow, fontWeight: FontWeight.w600,
        ),
        headlineMedium: GoogleFonts.cinzel(
          fontSize: 14, letterSpacing: 2.5, color: amberGlow, fontWeight: FontWeight.w500,
        ),
        headlineSmall: GoogleFonts.cinzel(
          fontSize: 11, letterSpacing: 2, color: paleGold, fontWeight: FontWeight.w500,
        ),
        bodyLarge: GoogleFonts.cormorantGaramond(
          fontSize: 16, height: 1.7, color: textLight,
        ),
        bodyMedium: GoogleFonts.cormorantGaramond(
          fontSize: 14, height: 1.6, color: textMuted,
        ),
        labelLarge: GoogleFonts.cinzel(
          fontSize: 11, letterSpacing: 1.5, color: textLight,
        ),
        labelSmall: GoogleFonts.cinzel(
          fontSize: 9, letterSpacing: 1.5, color: textMuted,
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: amberGlow,
          foregroundColor: deepSacred,
          textStyle: GoogleFonts.cinzel(fontSize: 11, letterSpacing: 2, fontWeight: FontWeight.w600),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: amberGlow,
          side: const BorderSide(color: cardBorder),
          textStyle: GoogleFonts.cinzel(fontSize: 10, letterSpacing: 1.5),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
        ),
      ),
      dividerTheme: const DividerThemeData(color: cardBorder, thickness: 1),
      sliderTheme: const SliderThemeData(
        activeTrackColor: amberGlow,
        inactiveTrackColor: cardBorder,
        thumbColor: amberGlow,
        overlayColor: Color(0x22D4A854),
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((s) =>
            s.contains(WidgetState.selected) ? amberGlow : textMuted),
        trackColor: WidgetStateProperty.resolveWith((s) =>
            s.contains(WidgetState.selected) ? const Color(0x44D4A854) : const Color(0x22FFFFFF)),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: cardBg,
        selectedColor: const Color(0x33D4A854),
        labelStyle: GoogleFonts.cinzel(fontSize: 10, letterSpacing: 1),
        side: const BorderSide(color: cardBorder),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
      ),
    );
  }
}
