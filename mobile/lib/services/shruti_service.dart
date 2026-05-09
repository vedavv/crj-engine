import 'dart:async';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';

import 'api_client.dart';

class ShrutiService {
  ShrutiService({ApiClient? apiClient, http.Client? httpClient})
      : _apiClient = apiClient ?? ApiClient(),
        _httpClient = httpClient ?? http.Client(),
        _player = AudioPlayer();

  final ApiClient _apiClient;
  final http.Client _httpClient;
  final AudioPlayer _player;

  double? _loadedSaHz;
  String? _loadedPattern;

  bool get isPlaying => _player.playing;
  Stream<bool> get playingStream => _player.playingStream;

  String _cacheKey(double saHz, String pattern) {
    final hzInt = (saHz * 100).round();
    return 'shruti_${pattern}_$hzInt.wav';
  }

  Future<File> _ensureCached(double saHz, String pattern) async {
    final dir = await getApplicationDocumentsDirectory();
    final file = File('${dir.path}/${_cacheKey(saHz, pattern)}');
    if (await file.exists() && await file.length() > 1000) {
      return file;
    }
    final url = '${_apiClient.baseUrl}/shruti'
        '?sa_hz=${saHz.toStringAsFixed(2)}&pattern=$pattern';
    final resp = await _httpClient.get(Uri.parse(url)).timeout(
          const Duration(seconds: 30),
        );
    if (resp.statusCode != 200) {
      throw Exception('Shruti fetch failed (${resp.statusCode}): ${resp.body}');
    }
    await file.writeAsBytes(resp.bodyBytes, flush: true);
    return file;
  }

  Future<void> play({required double saHz, required String pattern}) async {
    final needsLoad = saHz != _loadedSaHz || pattern != _loadedPattern;
    if (needsLoad) {
      final file = await _ensureCached(saHz, pattern);
      await _player.setFilePath(file.path);
      await _player.setLoopMode(LoopMode.all);
      await _player.setVolume(1.0);
      _loadedSaHz = saHz;
      _loadedPattern = pattern;
    }
    if (!_player.playing) {
      await _player.setVolume(1.0);
      await _player.play();
    }
  }

  Future<void> stop() async {
    await _player.stop();
  }

  /// Smoothly fade volume to zero over [duration] before stopping. Use this
  /// when recording starts so the Shruti doesn't bleed into the captured audio.
  Future<void> fadeOutAndStop({
    Duration duration = const Duration(milliseconds: 400),
  }) async {
    if (!_player.playing) return;
    const steps = 8;
    final stepDuration = Duration(
      milliseconds: duration.inMilliseconds ~/ steps,
    );
    final startVolume = _player.volume;
    for (var i = steps - 1; i >= 0; i--) {
      await _player.setVolume(startVolume * (i / steps));
      await Future<void>.delayed(stepDuration);
    }
    await _player.stop();
    await _player.setVolume(1.0);
  }

  void dispose() {
    _player.dispose();
    _httpClient.close();
  }
}
