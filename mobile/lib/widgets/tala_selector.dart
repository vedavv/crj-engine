import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../models/tala.dart';
import '../theme/soundscape_theme.dart';

/// 7-tala curated set for v1 — one per popular cycle across traditions.
const supportedTalaIds = <String>[
  'triputa_chatusra', // Adi (8) — Carnatic
  'rupaka_chatusra',  // Rupakam (6) — Carnatic
  'triputa_tisra',    // Tisra Triputa (7) — Carnatic
  'teentaal',         // Teentaal (16) — Hindustani
  'ektaal',           // Ektaal (12) — Hindustani
  'dadra',            // Dadra (6) — Hindustani
  'chautal',          // Chautal (12) — Dhrupad
];

/// Default instrument per tala — user can override.
const _defaultInstrumentByTala = <String, String>{
  'triputa_chatusra': 'mridangam',
  'rupaka_chatusra': 'mridangam',
  'triputa_tisra': 'mridangam',
  'teentaal': 'tabla',
  'ektaal': 'tabla',
  'dadra': 'tabla',
  'chautal': 'pakhavaj',
};

const _displayNameByTala = <String, String>{
  'triputa_chatusra': 'Adi (8)',
  'rupaka_chatusra': 'Rupakam (6)',
  'triputa_tisra': 'Tisra Triputa (7)',
  'teentaal': 'Teentaal (16)',
  'ektaal': 'Ektaal (12)',
  'dadra': 'Dadra (6)',
  'chautal': 'Chautal (12)',
};

String defaultInstrumentFor(String talaId) =>
    _defaultInstrumentByTala[talaId] ?? 'mridangam';

class TalaSelector extends StatelessWidget {
  final String selectedTalaId;
  final String selectedInstrument;
  final int tempoBpm;
  final ValueChanged<String> onTalaChanged;
  final ValueChanged<String> onInstrumentChanged;
  final ValueChanged<int> onTempoChanged;

  const TalaSelector({
    super.key,
    required this.selectedTalaId,
    required this.selectedInstrument,
    required this.tempoBpm,
    required this.onTalaChanged,
    required this.onInstrumentChanged,
    required this.onTempoChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Tala chips
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: supportedTalaIds.map((id) {
            final active = id == selectedTalaId;
            return GestureDetector(
              onTap: () {
                onTalaChanged(id);
                // When the tala changes, snap to its conventional instrument
                onInstrumentChanged(defaultInstrumentFor(id));
              },
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: active
                      ? SoundScapeTheme.amberGlow.withValues(alpha: 0.2)
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(
                    color: active
                        ? SoundScapeTheme.amberGlow
                        : SoundScapeTheme.cardBorder,
                  ),
                ),
                child: Text(
                  _displayNameByTala[id] ?? id,
                  style: GoogleFonts.cinzel(
                    fontSize: 10,
                    letterSpacing: 1,
                    color: active
                        ? SoundScapeTheme.amberGlow
                        : SoundScapeTheme.textLight,
                    fontWeight: active ? FontWeight.w600 : FontWeight.w400,
                  ),
                ),
              ),
            );
          }).toList(),
        ),
        const SizedBox(height: 12),
        // Instrument toggle
        Row(
          children: [
            for (final inst in const ['mridangam', 'pakhavaj', 'tabla', 'click'])
              Padding(
                padding: const EdgeInsets.only(right: 6),
                child: GestureDetector(
                  onTap: () => onInstrumentChanged(inst),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 5,
                    ),
                    decoration: BoxDecoration(
                      color: inst == selectedInstrument
                          ? SoundScapeTheme.amberGlow.withValues(alpha: 0.2)
                          : Colors.transparent,
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(
                        color: inst == selectedInstrument
                            ? SoundScapeTheme.amberGlow
                            : SoundScapeTheme.cardBorder,
                      ),
                    ),
                    child: Text(
                      inst.toUpperCase(),
                      style: GoogleFonts.cinzel(
                        fontSize: 9,
                        letterSpacing: 1,
                        color: inst == selectedInstrument
                            ? SoundScapeTheme.amberGlow
                            : SoundScapeTheme.textMuted,
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(height: 12),
        // Tempo slider
        Row(
          children: [
            Text(
              'TEMPO',
              style: GoogleFonts.cinzel(
                fontSize: 9,
                letterSpacing: 2,
                color: SoundScapeTheme.textMuted,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Slider(
                value: tempoBpm.toDouble(),
                min: 40,
                max: 200,
                divisions: 32, // 5 BPM steps
                onChanged: (v) => onTempoChanged(v.round()),
              ),
            ),
            SizedBox(
              width: 60,
              child: Text(
                '$tempoBpm BPM',
                style: GoogleFonts.cormorantGaramond(
                  fontSize: 13,
                  color: SoundScapeTheme.textLight,
                ),
                textAlign: TextAlign.right,
              ),
            ),
          ],
        ),
      ],
    );
  }
}
