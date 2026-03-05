import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../models/raga.dart';
import '../theme/soundscape_theme.dart';

class RagaCard extends StatelessWidget {
  final RagaCandidate raga;
  final bool isTop;

  const RagaCard({super.key, required this.raga, this.isTop = false});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: SoundScapeTheme.cardBg,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isTop
              ? SoundScapeTheme.amberGlow.withValues(alpha: 0.4)
              : SoundScapeTheme.cardBorder,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header row
          Row(
            children: [
              if (isTop)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  margin: const EdgeInsets.only(right: 8),
                  decoration: BoxDecoration(
                    color: SoundScapeTheme.amberGlow,
                    borderRadius: BorderRadius.circular(3),
                  ),
                  child: Text(
                    'TOP',
                    style: GoogleFonts.cinzel(
                      fontSize: 8,
                      fontWeight: FontWeight.w700,
                      color: SoundScapeTheme.deepSacred,
                      letterSpacing: 1,
                    ),
                  ),
                ),
              Expanded(
                child: Text(
                  '${raga.ragaName} (#${raga.ragaNumber})',
                  style: GoogleFonts.cinzel(
                    fontSize: 13,
                    color: isTop
                        ? SoundScapeTheme.amberGlow
                        : SoundScapeTheme.paleGold,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 1,
                  ),
                ),
              ),
              Text(
                '${(raga.confidence * 100).toStringAsFixed(1)}%',
                style: GoogleFonts.cinzel(
                  fontSize: 12,
                  color: SoundScapeTheme.amberGlow,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          // Confidence bar
          ClipRRect(
            borderRadius: BorderRadius.circular(3),
            child: LinearProgressIndicator(
              value: raga.confidence,
              minHeight: 6,
              backgroundColor: SoundScapeTheme.cardBorder,
              valueColor: AlwaysStoppedAnimation(
                isTop ? SoundScapeTheme.amberGlow : SoundScapeTheme.skyBlue,
              ),
            ),
          ),
          const SizedBox(height: 10),
          // Arohana / Avarohana
          _scaleRow('Arohana', raga.arohana),
          const SizedBox(height: 4),
          _scaleRow('Avarohana', raga.avarohana),
        ],
      ),
    );
  }

  Widget _scaleRow(String label, List<String> swaras) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 80,
          child: Text(
            label,
            style: GoogleFonts.cinzel(
              fontSize: 9,
              color: SoundScapeTheme.textMuted,
              letterSpacing: 1,
            ),
          ),
        ),
        Expanded(
          child: Text(
            swaras.join(' '),
            style: GoogleFonts.cormorantGaramond(
              fontSize: 13,
              color: SoundScapeTheme.textLight,
            ),
          ),
        ),
      ],
    );
  }
}
