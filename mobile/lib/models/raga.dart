class RagaCandidate {
  final int ragaNumber;
  final String ragaName;
  final double confidence;
  final List<String> arohana;
  final List<String> avarohana;

  const RagaCandidate({
    required this.ragaNumber,
    required this.ragaName,
    required this.confidence,
    required this.arohana,
    required this.avarohana,
  });

  factory RagaCandidate.fromJson(Map<String, dynamic> json) => RagaCandidate(
        ragaNumber: json['raga_number'] as int,
        ragaName: json['raga_name'] as String,
        confidence: (json['confidence'] as num).toDouble(),
        arohana: List<String>.from(json['arohana'] ?? []),
        avarohana: List<String>.from(json['avarohana'] ?? []),
      );
}
