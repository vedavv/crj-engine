import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../theme/soundscape_theme.dart';

class SwaraChip extends StatelessWidget {
  final String label;
  final bool isFixed;

  const SwaraChip({super.key, required this.label, this.isFixed = false});

  static const _swaraColors = {
    'Sa': Color(0xFFD4A854),
    'Ri': Color(0xFFE87831),
    'Ga': Color(0xFFC4607A),
    'Ma': Color(0xFF4A8FB8),
    'Pa': Color(0xFF5CAB7D),
    'Dha': Color(0xFFA066C4),
    'Ni': Color(0xFFCB6B4A),
  };

  Color get _color {
    for (final entry in _swaraColors.entries) {
      if (label.startsWith(entry.key)) return entry.value;
    }
    return SoundScapeTheme.amberGlow;
  }

  @override
  Widget build(BuildContext context) {
    final color = _color;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        label,
        style: GoogleFonts.cinzel(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: color,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}
