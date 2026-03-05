import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../theme/soundscape_theme.dart';

class ScriptSelector extends StatelessWidget {
  final String selected;
  final ValueChanged<String> onChanged;

  const ScriptSelector({
    super.key,
    required this.selected,
    required this.onChanged,
  });

  static const _scripts = [
    ('iast', 'IAST'),
    ('devanagari', 'देव'),
    ('kannada', 'ಕನ್ನ'),
    ('tamil', 'தமி'),
    ('telugu', 'తెలు'),
  ];

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: _scripts.map((s) {
        final isActive = s.$1 == selected;
        return Padding(
          padding: const EdgeInsets.only(right: 6),
          child: GestureDetector(
            onTap: () => onChanged(s.$1),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: isActive
                    ? SoundScapeTheme.amberGlow.withValues(alpha: 0.2)
                    : Colors.transparent,
                borderRadius: BorderRadius.circular(4),
                border: Border.all(
                  color: isActive
                      ? SoundScapeTheme.amberGlow
                      : SoundScapeTheme.cardBorder,
                ),
              ),
              child: Text(
                s.$2,
                style: GoogleFonts.cinzel(
                  fontSize: 10,
                  letterSpacing: 1,
                  color: isActive
                      ? SoundScapeTheme.amberGlow
                      : SoundScapeTheme.textMuted,
                  fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
                ),
              ),
            ),
          ),
        );
      }).toList(),
    );
  }
}
