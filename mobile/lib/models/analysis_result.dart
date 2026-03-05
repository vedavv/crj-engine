import 'raga.dart';

class PitchFrame {
  final double timestampMs;
  final double frequencyHz;
  final double confidence;

  const PitchFrame({
    required this.timestampMs,
    required this.frequencyHz,
    required this.confidence,
  });

  factory PitchFrame.fromJson(Map<String, dynamic> json) => PitchFrame(
        timestampMs: (json['timestamp_ms'] as num).toDouble(),
        frequencyHz: (json['frequency_hz'] as num).toDouble(),
        confidence: (json['confidence'] as num).toDouble(),
      );
}

class TranscribedNote {
  final double startMs;
  final double endMs;
  final String swaraId;
  final String octave;
  final double frequencyHz;
  final double centsDeviation;
  final double confidence;

  const TranscribedNote({
    required this.startMs,
    required this.endMs,
    required this.swaraId,
    required this.octave,
    required this.frequencyHz,
    required this.centsDeviation,
    required this.confidence,
  });

  factory TranscribedNote.fromJson(Map<String, dynamic> json) =>
      TranscribedNote(
        startMs: (json['start_ms'] as num).toDouble(),
        endMs: (json['end_ms'] as num).toDouble(),
        swaraId: json['swara_id'] as String,
        octave: json['octave'] as String,
        frequencyHz: (json['frequency_hz'] as num).toDouble(),
        centsDeviation: (json['cents_deviation'] as num).toDouble(),
        confidence: (json['confidence'] as num).toDouble(),
      );
}

class TranscribedPhrase {
  final List<TranscribedNote> notes;
  final double startMs;
  final double endMs;

  const TranscribedPhrase({
    required this.notes,
    required this.startMs,
    required this.endMs,
  });

  factory TranscribedPhrase.fromJson(Map<String, dynamic> json) =>
      TranscribedPhrase(
        notes: (json['notes'] as List)
            .map((n) => TranscribedNote.fromJson(n as Map<String, dynamic>))
            .toList(),
        startMs: (json['start_ms'] as num).toDouble(),
        endMs: (json['end_ms'] as num).toDouble(),
      );
}

class Gamaka {
  final double segmentStartMs;
  final double segmentEndMs;
  final String gamakaType;
  final double confidence;

  const Gamaka({
    required this.segmentStartMs,
    required this.segmentEndMs,
    required this.gamakaType,
    required this.confidence,
  });

  factory Gamaka.fromJson(Map<String, dynamic> json) => Gamaka(
        segmentStartMs: (json['segment_start_ms'] as num).toDouble(),
        segmentEndMs: (json['segment_end_ms'] as num).toDouble(),
        gamakaType: json['gamaka_type'] as String,
        confidence: (json['confidence'] as num).toDouble(),
      );
}

class AnalysisResult {
  final String status;
  final double durationS;
  final double referenceSaHz;
  final String algorithm;
  final List<String> uniqueSwaras;
  final List<String> swaraSequence;
  final String notationIast;
  final String notationCompact;
  final String notationRequested;
  final String script;
  final List<TranscribedPhrase> phrases;
  final List<Gamaka> gamakas;
  final List<RagaCandidate> ragaCandidates;
  final List<PitchFrame>? pitchContour;

  const AnalysisResult({
    this.status = 'success',
    required this.durationS,
    required this.referenceSaHz,
    required this.algorithm,
    required this.uniqueSwaras,
    required this.swaraSequence,
    required this.notationIast,
    required this.notationCompact,
    required this.notationRequested,
    required this.script,
    required this.phrases,
    required this.gamakas,
    required this.ragaCandidates,
    this.pitchContour,
  });

  factory AnalysisResult.fromJson(Map<String, dynamic> json) => AnalysisResult(
        status: json['status'] as String? ?? 'success',
        durationS: (json['duration_s'] as num).toDouble(),
        referenceSaHz: (json['reference_sa_hz'] as num).toDouble(),
        algorithm: json['algorithm'] as String,
        uniqueSwaras: List<String>.from(json['unique_swaras'] ?? []),
        swaraSequence: List<String>.from(json['swara_sequence'] ?? []),
        notationIast: json['notation_iast'] as String? ?? '',
        notationCompact: json['notation_compact'] as String? ?? '',
        notationRequested: json['notation_requested'] as String? ?? '',
        script: json['script'] as String? ?? 'iast',
        phrases: (json['phrases'] as List?)
                ?.map((p) =>
                    TranscribedPhrase.fromJson(p as Map<String, dynamic>))
                .toList() ??
            [],
        gamakas: (json['gamakas'] as List?)
                ?.map((g) => Gamaka.fromJson(g as Map<String, dynamic>))
                .toList() ??
            [],
        ragaCandidates: (json['raga_candidates'] as List?)
                ?.map(
                    (r) => RagaCandidate.fromJson(r as Map<String, dynamic>))
                .toList() ??
            [],
        pitchContour: (json['pitch_contour'] as List?)
            ?.map((p) => PitchFrame.fromJson(p as Map<String, dynamic>))
            .toList(),
      );

  Map<String, dynamic> toJson() => {
        'status': status,
        'duration_s': durationS,
        'reference_sa_hz': referenceSaHz,
        'algorithm': algorithm,
        'unique_swaras': uniqueSwaras,
        'swara_sequence': swaraSequence,
        'notation_iast': notationIast,
        'notation_compact': notationCompact,
        'notation_requested': notationRequested,
        'script': script,
        'phrases': phrases
            .map((p) => {
                  'notes': p.notes
                      .map((n) => {
                            'start_ms': n.startMs,
                            'end_ms': n.endMs,
                            'swara_id': n.swaraId,
                            'octave': n.octave,
                            'frequency_hz': n.frequencyHz,
                            'cents_deviation': n.centsDeviation,
                            'confidence': n.confidence,
                          })
                      .toList(),
                  'start_ms': p.startMs,
                  'end_ms': p.endMs,
                })
            .toList(),
        'gamakas': gamakas
            .map((g) => {
                  'segment_start_ms': g.segmentStartMs,
                  'segment_end_ms': g.segmentEndMs,
                  'gamaka_type': g.gamakaType,
                  'confidence': g.confidence,
                })
            .toList(),
        'raga_candidates': ragaCandidates
            .map((r) => {
                  'raga_number': r.ragaNumber,
                  'raga_name': r.ragaName,
                  'confidence': r.confidence,
                  'arohana': r.arohana,
                  'avarohana': r.avarohana,
                })
            .toList(),
      };
}
