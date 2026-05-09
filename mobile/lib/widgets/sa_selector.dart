import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import '../models/swara.dart';
import '../theme/soundscape_theme.dart';

class SaSelector extends StatelessWidget {
  final double selectedHz;
  final List<TuningPreset> presets;
  final ValueChanged<double> onChanged;

  const SaSelector({
    super.key,
    required this.selectedHz,
    required this.presets,
    required this.onChanged,
  });

  bool _matches(double a, double b) => (a - b).abs() < 0.05;

  @override
  Widget build(BuildContext context) {
    final isCustom = !presets.any((p) => _matches(p.referenceSaHz, selectedHz));

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final p in presets)
            Padding(
              padding: const EdgeInsets.only(right: 6),
              child: _Chip(
                label: p.westernReference,
                subLabel: '${p.referenceSaHz.toStringAsFixed(2)} Hz',
                active: _matches(p.referenceSaHz, selectedHz),
                onTap: () => onChanged(p.referenceSaHz),
              ),
            ),
          _Chip(
            label: 'Custom',
            subLabel: isCustom ? '${selectedHz.toStringAsFixed(2)} Hz' : '— Hz',
            active: isCustom,
            onTap: () => _openCustom(context),
          ),
        ],
      ),
    );
  }

  Future<void> _openCustom(BuildContext context) async {
    final controller = TextEditingController(
      text: selectedHz.toStringAsFixed(2),
    );
    final result = await showDialog<double>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: SoundScapeTheme.cardBg,
        title: Text(
          'CUSTOM Sa (Hz)',
          style: GoogleFonts.cinzel(
            fontSize: 13,
            letterSpacing: 2,
            color: SoundScapeTheme.amberGlow,
          ),
        ),
        content: TextField(
          controller: controller,
          autofocus: true,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(r'[0-9.]')),
          ],
          style: GoogleFonts.cormorantGaramond(
            fontSize: 18,
            color: SoundScapeTheme.textLight,
          ),
          decoration: InputDecoration(
            hintText: 'e.g. 261.63',
            hintStyle: TextStyle(color: SoundScapeTheme.textMuted),
            suffixText: 'Hz',
            suffixStyle: TextStyle(color: SoundScapeTheme.textMuted),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('CANCEL'),
          ),
          TextButton(
            onPressed: () {
              final v = double.tryParse(controller.text.trim());
              if (v != null && v >= 50 && v <= 1000) Navigator.pop(ctx, v);
            },
            child: const Text('SET'),
          ),
        ],
      ),
    );
    if (result != null) onChanged(result);
  }
}

class _Chip extends StatelessWidget {
  final String label;
  final String subLabel;
  final bool active;
  final VoidCallback onTap;

  const _Chip({
    required this.label,
    required this.subLabel,
    required this.active,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
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
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              label,
              style: GoogleFonts.cinzel(
                fontSize: 11,
                letterSpacing: 1.2,
                color: active
                    ? SoundScapeTheme.amberGlow
                    : SoundScapeTheme.textLight,
                fontWeight: active ? FontWeight.w600 : FontWeight.w400,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              subLabel,
              style: GoogleFonts.cormorantGaramond(
                fontSize: 11,
                color: SoundScapeTheme.textMuted,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
