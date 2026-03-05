import 'dart:io';
import 'dart:typed_data';

import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

class AudioService {
  final AudioPlayer player = AudioPlayer();
  final AudioRecorder recorder = AudioRecorder();

  bool get isPlaying => player.playing;

  Stream<Duration> get positionStream => player.positionStream;
  Stream<Duration?> get durationStream => player.durationStream;
  Stream<PlayerState> get playerStateStream => player.playerStateStream;

  // ── Playback ───────────────────────────────────────────────────────────

  Future<void> playAsset(String assetPath) async {
    await player.setAsset(assetPath);
    await player.play();
  }

  Future<void> playUrl(String url) async {
    await player.setUrl(url);
    await player.play();
  }

  Future<void> playBytes(Uint8List bytes, {String ext = 'wav'}) async {
    final dir = await getTemporaryDirectory();
    final file = File('${dir.path}/compose_preview.$ext');
    await file.writeAsBytes(bytes);
    await player.setFilePath(file.path);
    await player.play();
  }

  Future<void> pause() => player.pause();
  Future<void> resume() => player.play();
  Future<void> stop() => player.stop();
  Future<void> seek(Duration position) => player.seek(position);
  Future<void> setSpeed(double speed) => player.setSpeed(speed);
  Future<void> setVolume(double volume) => player.setVolume(volume);

  // ── Recording ──────────────────────────────────────────────────────────

  Future<bool> hasPermission() => recorder.hasPermission();

  Future<String> startRecording() async {
    final dir = await getTemporaryDirectory();
    final path = '${dir.path}/crj_recording.m4a';
    await recorder.start(
      const RecordConfig(encoder: AudioEncoder.aacLc, sampleRate: 44100),
      path: path,
    );
    return path;
  }

  Future<String?> stopRecording() => recorder.stop();

  // ── Cleanup ────────────────────────────────────────────────────────────

  void dispose() {
    player.dispose();
    recorder.dispose();
  }
}
