import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../services/api_client.dart';
import '../theme/soundscape_theme.dart';

/// Returns the chosen Sa Hz, or null if the user dismissed without picking.
Future<double?> showSaSuggestionDialog(
  BuildContext context, {
  required TonicSuggestion suggestion,
  required double currentSaHz,
}) {
  return showDialog<double>(
    context: context,
    barrierDismissible: false,
    builder: (ctx) => _SaSuggestionDialog(
      suggestion: suggestion,
      currentSaHz: currentSaHz,
    ),
  );
}

class _SaSuggestionDialog extends StatelessWidget {
  final TonicSuggestion suggestion;
  final double currentSaHz;

  const _SaSuggestionDialog({
    required this.suggestion,
    required this.currentSaHz,
  });

  String _confidenceLabel(double c) {
    if (c >= 0.7) return 'High';
    if (c >= 0.4) return 'Medium';
    if (c > 0.0) return 'Low';
    return 'Very low';
  }

  Color _confidenceColor(double c) {
    if (c >= 0.7) return SoundScapeTheme.amberGlow;
    if (c >= 0.4) return SoundScapeTheme.sacredSaffron;
    return SoundScapeTheme.lotusPink;
  }

  @override
  Widget build(BuildContext context) {
    final lowConfidence = suggestion.confidence < 0.3;

    return AlertDialog(
      backgroundColor: SoundScapeTheme.cardBg,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: const BorderSide(color: SoundScapeTheme.cardBorder),
      ),
      title: Text(
        'DETECTED Sa',
        style: GoogleFonts.cinzel(
          fontSize: 13,
          letterSpacing: 2,
          color: SoundScapeTheme.amberGlow,
        ),
      ),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (lowConfidence)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                  'Couldn’t lock onto a clear tonic. You may want to '
                  'pick Sa manually.',
                  style: GoogleFonts.cormorantGaramond(
                    fontSize: 13,
                    color: SoundScapeTheme.lotusPink,
                  ),
                ),
              ),
            Text(
              suggestion.westernLabel,
              textAlign: TextAlign.center,
              style: GoogleFonts.cinzel(
                fontSize: 32,
                color: SoundScapeTheme.amberGlow,
                fontWeight: FontWeight.w600,
              ),
            ),
            Text(
              '${suggestion.suggestedSaHz.toStringAsFixed(2)} Hz',
              textAlign: TextAlign.center,
              style: GoogleFonts.cormorantGaramond(
                fontSize: 16,
                color: SoundScapeTheme.textLight,
              ),
            ),
            const SizedBox(height: 8),
            Center(
              child: _ConfidenceBar(
                label: _confidenceLabel(suggestion.confidence),
                value: suggestion.confidence,
                color: _confidenceColor(suggestion.confidence),
              ),
            ),
            if (suggestion.candidates.length > 1) ...[
              const SizedBox(height: 16),
              Text(
                'OTHER POSSIBILITIES',
                style: GoogleFonts.cinzel(
                  fontSize: 9,
                  letterSpacing: 2,
                  color: SoundScapeTheme.textMuted,
                ),
              ),
              const SizedBox(height: 8),
              for (final c in suggestion.candidates.skip(1).take(2))
                _AlternativeRow(candidate: c),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, currentSaHz),
          child: Text(
            'KEEP CURRENT',
            style: GoogleFonts.cinzel(
              fontSize: 10,
              letterSpacing: 1.5,
              color: SoundScapeTheme.textMuted,
            ),
          ),
        ),
        TextButton(
          onPressed: () =>
              Navigator.pop(context, suggestion.suggestedSaHz),
          child: Text(
            'USE Sa',
            style: GoogleFonts.cinzel(
              fontSize: 11,
              letterSpacing: 1.5,
              color: SoundScapeTheme.amberGlow,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ],
    );
  }
}

class _ConfidenceBar extends StatelessWidget {
  final String label;
  final double value;
  final Color color;

  const _ConfidenceBar({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          'CONFIDENCE: $label',
          style: GoogleFonts.cinzel(
            fontSize: 9,
            letterSpacing: 1.5,
            color: color,
          ),
        ),
        const SizedBox(height: 4),
        SizedBox(
          width: 160,
          height: 4,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(2),
            child: LinearProgressIndicator(
              value: value.clamp(0.0, 1.0),
              backgroundColor: SoundScapeTheme.cardBorder,
              valueColor: AlwaysStoppedAnimation<Color>(color),
            ),
          ),
        ),
      ],
    );
  }
}

class _AlternativeRow extends StatelessWidget {
  final TonicCandidate candidate;

  const _AlternativeRow({required this.candidate});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () => Navigator.pop(context, candidate.saHz),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          children: [
            SizedBox(
              width: 48,
              child: Text(
                candidate.westernLabel,
                style: GoogleFonts.cinzel(
                  fontSize: 14,
                  color: SoundScapeTheme.textLight,
                ),
              ),
            ),
            Expanded(
              child: Text(
                '${candidate.saHz.toStringAsFixed(2)} Hz',
                style: GoogleFonts.cormorantGaramond(
                  fontSize: 13,
                  color: SoundScapeTheme.textMuted,
                ),
              ),
            ),
            Text(
              '${(candidate.confidence * 100).toStringAsFixed(0)}%',
              style: GoogleFonts.cormorantGaramond(
                fontSize: 12,
                color: SoundScapeTheme.textMuted,
              ),
            ),
            const SizedBox(width: 8),
            Icon(
              Icons.chevron_right_rounded,
              size: 16,
              color: SoundScapeTheme.textMuted,
            ),
          ],
        ),
      ),
    );
  }
}
