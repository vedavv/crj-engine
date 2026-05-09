import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../models/analysis_result.dart';
import '../models/raga.dart';
import '../models/swara.dart';
import '../models/tala.dart';

class ApiClient {
  static const _defaultBaseUrl =
      'https://crj-engine-179031859093.asia-south1.run.app/api/v1';

  final http.Client _client;
  final String baseUrl;

  ApiClient({http.Client? client, String? baseUrl})
      : _client = client ?? http.Client(),
        baseUrl = baseUrl ?? _defaultBaseUrl;

  // ── Health ──────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> health() async {
    final resp = await _client.get(Uri.parse('$baseUrl/health'));
    _check(resp);
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  // ── Reference data ─────────────────────────────────────────────────────

  Future<List<Swarasthana>> getSwarasthanas() async {
    final resp = await _client.get(Uri.parse('$baseUrl/swarasthanas'));
    _check(resp);
    final list = jsonDecode(resp.body) as List;
    return list
        .map((e) => Swarasthana.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<TuningPreset>> getTuningPresets() async {
    final resp = await _client.get(Uri.parse('$baseUrl/tuning-presets'));
    _check(resp);
    final list = jsonDecode(resp.body) as List;
    return list
        .map((e) => TuningPreset.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<RagaCandidate>> getRagas() async {
    final resp = await _client.get(Uri.parse('$baseUrl/ragas'));
    _check(resp);
    final list = jsonDecode(resp.body) as List;
    return list
        .map((e) => RagaCandidate.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<Tala>> getTalas() async {
    final resp = await _client.get(Uri.parse('$baseUrl/talas'));
    _check(resp);
    final list = jsonDecode(resp.body) as List;
    return list
        .map((e) => Tala.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // ── Analysis ───────────────────────────────────────────────────────────

  Future<AnalysisResult> analyze(
    File audioFile, {
    String algorithm = 'crepe',
    double saHz = 261.63,
    String script = 'iast',
  }) async {
    final uri = Uri.parse('$baseUrl/analyze');
    final request = http.MultipartRequest('POST', uri)
      ..fields['algorithm'] = algorithm
      ..fields['reference_sa_hz'] = saHz.toString()
      ..fields['script'] = script
      ..files.add(await http.MultipartFile.fromPath('file', audioFile.path));

    final streamed = await _client.send(request).timeout(
      const Duration(minutes: 10),
      onTimeout: () => throw ApiException(
        408,
        'Analysis timed out after 10 minutes. Try a shorter clip.',
      ),
    );
    final resp = await http.Response.fromStream(streamed);
    _check(resp);
    return AnalysisResult.fromJson(
        jsonDecode(resp.body) as Map<String, dynamic>);
  }

  // ── Sa auto-detection ─────────────────────────────────────────────────

  Future<TonicSuggestion> detectSa(File audioFile) async {
    final uri = Uri.parse('$baseUrl/detect-sa');
    final request = http.MultipartRequest('POST', uri)
      ..files.add(await http.MultipartFile.fromPath('file', audioFile.path));

    final streamed = await _client.send(request).timeout(
          const Duration(minutes: 2),
          onTimeout: () => throw ApiException(
            408,
            'Sa detection timed out.',
          ),
        );
    final resp = await http.Response.fromStream(streamed);
    _check(resp);
    return TonicSuggestion.fromJson(
      jsonDecode(resp.body) as Map<String, dynamic>,
    );
  }

  // ── Compose (text notation → WAV) ─────────────────────────────────────

  Future<Uint8List> compose(
    String notation, {
    String tone = 'voice',
    double tempoBpm = 60.0,
    int speed = 1,
    String? talaId,
    bool tanpura = false,
    bool clickTrack = false,
  }) async {
    final body = <String, dynamic>{
      'notation': notation,
      'tone': tone,
      'tempo_bpm': tempoBpm,
      'speed': speed,
      'include_tanpura': tanpura,
      'include_click_track': clickTrack,
    };
    if (talaId != null) body['tala_id'] = talaId;

    final resp = await _client.post(
      Uri.parse('$baseUrl/compose'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(resp);
    return resp.bodyBytes;
  }

  // ── Export PDF ─────────────────────────────────────────────────────────

  Future<Uint8List> exportPdf(AnalysisResult data,
      {String script = 'iast'}) async {
    final payload = data.toJson();
    payload['export_script'] = script;

    final resp = await _client.post(
      Uri.parse('$baseUrl/export/pdf'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );
    _check(resp);
    return resp.bodyBytes;
  }

  // ── Helpers ────────────────────────────────────────────────────────────

  void _check(http.Response resp) {
    if (resp.statusCode >= 400) {
      throw ApiException(resp.statusCode, resp.body);
    }
  }

  void dispose() => _client.close();
}

class ApiException implements Exception {
  final int statusCode;
  final String body;
  ApiException(this.statusCode, this.body);

  @override
  String toString() => 'ApiException($statusCode): $body';
}

class TonicCandidate {
  final double saHz;
  final String westernLabel;
  final double confidence;
  final bool hasPerfectFifth;

  const TonicCandidate({
    required this.saHz,
    required this.westernLabel,
    required this.confidence,
    required this.hasPerfectFifth,
  });

  factory TonicCandidate.fromJson(Map<String, dynamic> j) => TonicCandidate(
        saHz: (j['sa_hz'] as num).toDouble(),
        westernLabel: j['western_label'] as String,
        confidence: (j['confidence'] as num).toDouble(),
        hasPerfectFifth: j['has_perfect_fifth'] as bool? ?? false,
      );
}

class TonicSuggestion {
  final double suggestedSaHz;
  final String westernLabel;
  final double confidence;
  final List<TonicCandidate> candidates;
  final int voicedFrameCount;

  const TonicSuggestion({
    required this.suggestedSaHz,
    required this.westernLabel,
    required this.confidence,
    required this.candidates,
    required this.voicedFrameCount,
  });

  factory TonicSuggestion.fromJson(Map<String, dynamic> j) => TonicSuggestion(
        suggestedSaHz: (j['suggested_sa_hz'] as num).toDouble(),
        westernLabel: j['western_label'] as String,
        confidence: (j['confidence'] as num).toDouble(),
        candidates: (j['candidates'] as List)
            .map((e) => TonicCandidate.fromJson(e as Map<String, dynamic>))
            .toList(),
        voicedFrameCount: j['voiced_frame_count'] as int,
      );
}
