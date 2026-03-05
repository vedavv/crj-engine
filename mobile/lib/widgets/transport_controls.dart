import 'package:flutter/material.dart';

import '../theme/soundscape_theme.dart';

class TransportControls extends StatelessWidget {
  final bool isPlaying;
  final VoidCallback onPlayPause;
  final VoidCallback? onPrevious;
  final VoidCallback? onNext;
  final VoidCallback? onRewind;
  final VoidCallback? onForward;

  const TransportControls({
    super.key,
    required this.isPlaying,
    required this.onPlayPause,
    this.onPrevious,
    this.onNext,
    this.onRewind,
    this.onForward,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (onPrevious != null)
          _btn(Icons.skip_previous_rounded, onPrevious!, 28),
        const SizedBox(width: 8),
        if (onRewind != null)
          _btn(Icons.replay_10_rounded, onRewind!, 26),
        const SizedBox(width: 12),
        // Play / Pause — large central button
        GestureDetector(
          onTap: onPlayPause,
          child: Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: SoundScapeTheme.amberGlow,
              boxShadow: [
                BoxShadow(
                  color: SoundScapeTheme.amberGlow.withValues(alpha: 0.3),
                  blurRadius: 20,
                  spreadRadius: 4,
                ),
              ],
            ),
            child: Icon(
              isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded,
              color: SoundScapeTheme.deepSacred,
              size: 32,
            ),
          ),
        ),
        const SizedBox(width: 12),
        if (onForward != null)
          _btn(Icons.forward_10_rounded, onForward!, 26),
        const SizedBox(width: 8),
        if (onNext != null)
          _btn(Icons.skip_next_rounded, onNext!, 28),
      ],
    );
  }

  Widget _btn(IconData icon, VoidCallback onTap, double size) {
    return IconButton(
      onPressed: onTap,
      icon: Icon(icon, size: size),
      color: SoundScapeTheme.textLight,
      splashRadius: 22,
    );
  }
}
