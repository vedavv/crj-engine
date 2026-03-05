import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/soundscape_theme.dart';

class WaveformVisualiser extends StatefulWidget {
  final bool playing;
  final double height;

  const WaveformVisualiser({super.key, this.playing = false, this.height = 80});

  @override
  State<WaveformVisualiser> createState() => _WaveformVisualiserState();
}

class _WaveformVisualiserState extends State<WaveformVisualiser>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    )..repeat();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _ctrl,
      builder: (context, _) => CustomPaint(
        size: Size(double.infinity, widget.height),
        painter: _WaveformPainter(
          phase: _ctrl.value * 2 * math.pi,
          active: widget.playing,
        ),
      ),
    );
  }
}

class _WaveformPainter extends CustomPainter {
  final double phase;
  final bool active;

  _WaveformPainter({required this.phase, required this.active});

  @override
  void paint(Canvas canvas, Size size) {
    final midY = size.height / 2;
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;

    // Draw two sine waves
    for (int w = 0; w < 2; w++) {
      final path = Path();
      final amp = active ? (size.height * 0.35 - w * 8) : 4.0;
      final freq = 2.0 + w * 0.7;
      final offset = w * 0.8;

      paint.color = w == 0
          ? SoundScapeTheme.amberGlow.withValues(alpha: 0.8)
          : SoundScapeTheme.sacredSaffron.withValues(alpha: 0.4);

      for (double x = 0; x <= size.width; x += 2) {
        final t = x / size.width;
        final y = midY + amp * math.sin(freq * math.pi * t + phase + offset);
        if (x == 0) {
          path.moveTo(x, y);
        } else {
          path.lineTo(x, y);
        }
      }
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(_WaveformPainter old) =>
      old.phase != phase || old.active != active;
}
