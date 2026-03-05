class Tala {
  final String id;
  final String name;
  final String baseTala;
  final String jati;
  final int jatiCount;
  final List<String> components;
  final List<int> beatPattern;
  final int totalAksharas;
  final List<String> aliases;

  const Tala({
    required this.id,
    required this.name,
    required this.baseTala,
    required this.jati,
    required this.jatiCount,
    required this.components,
    required this.beatPattern,
    required this.totalAksharas,
    this.aliases = const [],
  });

  factory Tala.fromJson(Map<String, dynamic> json) => Tala(
        id: json['id'] as String,
        name: json['name'] as String,
        baseTala: json['base_tala'] as String,
        jati: json['jati'] as String,
        jatiCount: json['jati_count'] as int,
        components: List<String>.from(json['components'] ?? []),
        beatPattern: List<int>.from(json['beat_pattern'] ?? []),
        totalAksharas: json['total_aksharas'] as int,
        aliases: List<String>.from(json['aliases'] ?? []),
      );
}
