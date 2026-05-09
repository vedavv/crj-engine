import 'dart:async';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';

import 'api_client.dart';

class TalaService {
  TalaService({ApiClient? apiClient, http.Client? httpClient})
      : _apiClient = apiClient ?? ApiClient(),
        _httpClient = httpClient ?? http.Client(),
        _player = AudioPlayer();

  final ApiClient _apiClient;
  final http.Client _httpClient;
  final AudioPlayer _player;

  String? _loadedKey;

  bool get isPlaying => _player.playing;
  Stream<bool> get playingStream => _player.playingStream;
  Stream<Duration> get positionStream => _player.positionStream;
  Stream<Duration?> get durationStream => _player.durationStream;

  String _key(String talaId, String instrument, int tempoBpm, int cycles) =>
      'tala_${talaId}_${instrument}_${tempoBpm}bpm_${cycles}c.wav';

  Future<File> _ensureCached({
    required String talaId,
    required String instrument,
    required int tempoBpm,
    required int numCycles,
  }) async {
    final dir = await getApplicationDocumentsDirectory();
    final file = File(
      '${dir.path}/${_key(talaId, instrument, tempoBpm, numCycles)}',
    );
    if (await file.exists() && await file.length() > 1000) {
      return file;
    }
    final url = Uri.parse('${_apiClient.baseUrl}/tala-loop').replace(
      queryParameters: {
        'tala_id': talaId,
        'instrument': instrument,
        'tempo_bpm': tempoBpm.toString(),
        'num_cycles': numCycles.toString(),
      },
    );
    final resp = await _httpClient.get(url).timeout(
          const Duration(seconds: 60),
        );
    if (resp.statusCode != 200) {
      throw Exception('Tala fetch failed (${resp.statusCode}): ${resp.body}');
    }
    await file.writeAsBytes(resp.bodyBytes, flush: true);
    return file;
  }

  Future<void> play({
    required String talaId,
    required String instrument,
    required int tempoBpm,
    int numCycles = 4,
  }) async {
    final newKey = _key(talaId, instrument, tempoBpm, numCycles);
    if (newKey != _loadedKey) {
      final file = await _ensureCached(
        talaId: talaId,
        instrument: instrument,
        tempoBpm: tempoBpm,
        numCycles: numCycles,
      );
      await _player.setFilePath(file.path);
      await _player.setLoopMode(LoopMode.all);
      await _player.setVolume(1.0);
      _loadedKey = newKey;
    }
    if (!_player.playing) {
      await _player.setVolume(1.0);
      await _player.play();
    }
  }

  Future<void> stop() async {
    await _player.stop();
  }

  Future<void> fadeOutAndStop({
    Duration duration = const Duration(milliseconds: 400),
  }) async {
    if (!_player.playing) return;
    const steps = 8;
    final stepDuration =
        Duration(milliseconds: duration.inMilliseconds ~/ steps);
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
