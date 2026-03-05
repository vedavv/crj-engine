import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:just_audio/just_audio.dart';
import 'package:provider/provider.dart';

import '../services/audio_service.dart';
import '../theme/soundscape_theme.dart';
import '../widgets/transport_controls.dart';
import '../widgets/waveform_painter.dart';

class PlayerScreen extends StatefulWidget {
  const PlayerScreen({super.key});

  @override
  State<PlayerScreen> createState() => _PlayerScreenState();
}

class _PlayerScreenState extends State<PlayerScreen> {
  int _currentTrack = -1;
  double _speed = 1.0;
  double _volume = 0.8;

  static const _tracks = [
    _Track('Sama 1 — Setu', 'assets/audio/Sama_1_Setu.m4a', '3:42'),
    _Track('Sama 2 — Archika', 'web/audio/Sama_2_Archika.m4a', '4:15'),
    _Track('Sama 3 — Dvarchika', 'web/audio/Sama_3_Dvarchika.m4a', '5:08'),
    _Track('Sama 4 — Kayika', 'web/audio/Sama_4_Kayika.m4a', '3:56'),
    _Track('Sama 5 — Uhagana', 'web/audio/Sama_5_Uhagana.m4a', '6:23'),
    _Track('Sama 6 — Uhyagana', 'web/audio/Sama_6_Uhyagana.m4a', '4:47'),
  ];

  AudioService get _audio => context.read<AudioService>();

  Future<void> _play(int index) async {
    setState(() => _currentTrack = index);
    final track = _tracks[index];
    if (index == 0) {
      await _audio.playAsset(track.path);
    } else {
      // For other tracks, try the asset path
      try {
        await _audio.playAsset(track.path);
      } catch (_) {
        // Track not bundled — skip silently
      }
    }
  }

  void _togglePlayPause() {
    if (_audio.isPlaying) {
      _audio.pause();
    } else if (_currentTrack >= 0) {
      _audio.resume();
    } else {
      _play(0);
    }
  }

  void _prev() {
    if (_currentTrack > 0) _play(_currentTrack - 1);
  }

  void _next() {
    if (_currentTrack < _tracks.length - 1) _play(_currentTrack + 1);
  }

  void _seekDelta(int seconds) {
    final player = _audio.player;
    final pos = player.position + Duration(seconds: seconds);
    _audio.seek(pos < Duration.zero ? Duration.zero : pos);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('SACRED AUDIO ARCHIVE')),
      body: Column(
        children: [
          // Now playing area
          _NowPlaying(
            trackName:
                _currentTrack >= 0 ? _tracks[_currentTrack].title : null,
            audio: _audio,
            speed: _speed,
            volume: _volume,
            onPlayPause: _togglePlayPause,
            onPrev: _prev,
            onNext: _next,
            onRewind: () => _seekDelta(-10),
            onForward: () => _seekDelta(10),
            onSpeedChanged: (s) {
              setState(() => _speed = s);
              _audio.setSpeed(s);
            },
            onVolumeChanged: (v) {
              setState(() => _volume = v);
              _audio.setVolume(v);
            },
          ),
          // Track list
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              itemCount: _tracks.length,
              itemBuilder: (context, i) {
                final t = _tracks[i];
                final active = i == _currentTrack;
                return _TrackTile(
                  title: t.title,
                  duration: t.duration,
                  active: active,
                  onTap: () => _play(i),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _Track {
  final String title;
  final String path;
  final String duration;
  const _Track(this.title, this.path, this.duration);
}

class _NowPlaying extends StatelessWidget {
  final String? trackName;
  final AudioService audio;
  final double speed;
  final double volume;
  final VoidCallback onPlayPause;
  final VoidCallback onPrev;
  final VoidCallback onNext;
  final VoidCallback onRewind;
  final VoidCallback onForward;
  final ValueChanged<double> onSpeedChanged;
  final ValueChanged<double> onVolumeChanged;

  const _NowPlaying({
    required this.trackName,
    required this.audio,
    required this.speed,
    required this.volume,
    required this.onPlayPause,
    required this.onPrev,
    required this.onNext,
    required this.onRewind,
    required this.onForward,
    required this.onSpeedChanged,
    required this.onVolumeChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFF1A0F2E), SoundScapeTheme.deepSacred],
        ),
      ),
      child: Column(
        children: [
          // Track name
          Text(
            trackName ?? 'Select a track',
            style: GoogleFonts.cinzel(
              fontSize: 14,
              color: SoundScapeTheme.paleGold,
              letterSpacing: 2,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 16),
          // Waveform
          StreamBuilder<PlayerState>(
            stream: audio.playerStateStream,
            builder: (_, snap) => WaveformVisualiser(
              playing: snap.data?.playing ?? false,
              height: 60,
            ),
          ),
          const SizedBox(height: 12),
          // Seek bar
          StreamBuilder<Duration>(
            stream: audio.positionStream,
            builder: (_, posSnap) {
              final pos = posSnap.data ?? Duration.zero;
              return StreamBuilder<Duration?>(
                stream: audio.durationStream,
                builder: (_, durSnap) {
                  final dur = durSnap.data ?? const Duration(seconds: 1);
                  final maxVal = dur.inMilliseconds.toDouble();
                  return Column(
                    children: [
                      Slider(
                        value: pos.inMilliseconds
                            .toDouble()
                            .clamp(0, maxVal),
                        max: maxVal > 0 ? maxVal : 1,
                        onChanged: (v) =>
                            audio.seek(Duration(milliseconds: v.toInt())),
                      ),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(_fmt(pos),
                                style: _timeStyle),
                            Text(_fmt(dur),
                                style: _timeStyle),
                          ],
                        ),
                      ),
                    ],
                  );
                },
              );
            },
          ),
          const SizedBox(height: 8),
          // Transport
          StreamBuilder<PlayerState>(
            stream: audio.playerStateStream,
            builder: (_, snap) => TransportControls(
              isPlaying: snap.data?.playing ?? false,
              onPlayPause: onPlayPause,
              onPrevious: onPrev,
              onNext: onNext,
              onRewind: onRewind,
              onForward: onForward,
            ),
          ),
          const SizedBox(height: 12),
          // Speed + Volume row
          Row(
            children: [
              // Speed selector
              Text('Speed', style: _labelStyle),
              const SizedBox(width: 8),
              ...[0.5, 0.75, 1.0, 1.25, 1.5].map((s) => Padding(
                    padding: const EdgeInsets.only(right: 4),
                    child: _SpeedChip(
                      label: '${s}x',
                      active: speed == s,
                      onTap: () => onSpeedChanged(s),
                    ),
                  )),
              const Spacer(),
              // Volume
              Icon(Icons.volume_up_rounded,
                  size: 16, color: SoundScapeTheme.textMuted),
              SizedBox(
                width: 80,
                child: Slider(
                  value: volume,
                  onChanged: onVolumeChanged,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  static final _timeStyle = GoogleFonts.cormorantGaramond(
    fontSize: 12,
    color: SoundScapeTheme.textMuted,
  );

  static final _labelStyle = GoogleFonts.cinzel(
    fontSize: 9,
    letterSpacing: 1,
    color: SoundScapeTheme.textMuted,
  );

  static String _fmt(Duration d) {
    final m = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final s = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$m:$s';
  }
}

class _SpeedChip extends StatelessWidget {
  final String label;
  final bool active;
  final VoidCallback onTap;

  const _SpeedChip({
    required this.label,
    required this.active,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
        decoration: BoxDecoration(
          color: active
              ? SoundScapeTheme.amberGlow.withValues(alpha: 0.2)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(3),
          border: Border.all(
            color: active
                ? SoundScapeTheme.amberGlow
                : SoundScapeTheme.cardBorder,
          ),
        ),
        child: Text(
          label,
          style: GoogleFonts.cinzel(
            fontSize: 9,
            color: active
                ? SoundScapeTheme.amberGlow
                : SoundScapeTheme.textMuted,
          ),
        ),
      ),
    );
  }
}

class _TrackTile extends StatelessWidget {
  final String title;
  final String duration;
  final bool active;
  final VoidCallback onTap;

  const _TrackTile({
    required this.title,
    required this.duration,
    required this.active,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        margin: const EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(
          color: active
              ? SoundScapeTheme.amberGlow.withValues(alpha: 0.08)
              : SoundScapeTheme.cardBg,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: active
                ? SoundScapeTheme.amberGlow.withValues(alpha: 0.4)
                : SoundScapeTheme.cardBorder,
          ),
        ),
        child: Row(
          children: [
            Icon(
              active ? Icons.equalizer_rounded : Icons.music_note_rounded,
              color: active
                  ? SoundScapeTheme.amberGlow
                  : SoundScapeTheme.textMuted,
              size: 20,
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                title,
                style: GoogleFonts.cormorantGaramond(
                  fontSize: 15,
                  color: active
                      ? SoundScapeTheme.amberGlow
                      : SoundScapeTheme.textLight,
                  fontWeight: active ? FontWeight.w600 : FontWeight.w400,
                ),
              ),
            ),
            Text(
              duration,
              style: GoogleFonts.cormorantGaramond(
                fontSize: 13,
                color: SoundScapeTheme.textMuted,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
