class Swarasthana {
  final int index;
  final String id;
  final double cents;
  final String westernEquivalent;
  final Map<String, String> names;
  final Map<String, String> fullNames;
  final bool isFixed;
  final List<String> aliases;

  const Swarasthana({
    required this.index,
    required this.id,
    required this.cents,
    required this.westernEquivalent,
    required this.names,
    required this.fullNames,
    required this.isFixed,
    this.aliases = const [],
  });

  factory Swarasthana.fromJson(Map<String, dynamic> json) => Swarasthana(
        index: json['index'] as int,
        id: json['id'] as String,
        cents: (json['cents'] as num).toDouble(),
        westernEquivalent: json['western_equivalent'] as String,
        names: Map<String, String>.from(json['names'] as Map),
        fullNames: Map<String, String>.from(json['full_names'] as Map),
        isFixed: json['is_fixed'] as bool,
        aliases: List<String>.from(json['aliases'] ?? []),
      );

  String nameIn(String script) => names[script] ?? names['iast'] ?? id;
}

class TuningPreset {
  final String id;
  final String description;
  final double referenceSaHz;
  final String westernReference;

  const TuningPreset({
    required this.id,
    required this.description,
    required this.referenceSaHz,
    required this.westernReference,
  });

  factory TuningPreset.fromJson(Map<String, dynamic> json) => TuningPreset(
        id: json['id'] as String,
        description: json['description'] as String,
        referenceSaHz: (json['reference_sa_hz'] as num).toDouble(),
        westernReference: json['western_reference'] as String,
      );
}
