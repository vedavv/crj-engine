class SwaraIn {
  final String swaraId;
  final String octave;

  const SwaraIn({required this.swaraId, this.octave = 'madhya'});

  Map<String, dynamic> toJson() => {'swara_id': swaraId, 'octave': octave};
}

class BarIn {
  final String talaId;
  final int speed;
  final List<dynamic> swaras;
  final List<String> saahitya;

  const BarIn({
    required this.talaId,
    this.speed = 1,
    required this.swaras,
    this.saahitya = const [],
  });

  Map<String, dynamic> toJson() => {
        'tala_id': talaId,
        'speed': speed,
        'swaras': swaras
            .map((s) => s is SwaraIn ? s.toJson() : s as String)
            .toList(),
        'saahitya': saahitya,
      };
}

class LineIn {
  final List<BarIn> bars;
  final int repeat;

  const LineIn({required this.bars, this.repeat = 2});

  Map<String, dynamic> toJson() => {
        'bars': bars.map((b) => b.toJson()).toList(),
        'repeat': repeat,
      };
}

class SectionIn {
  final String name;
  final List<LineIn> lines;

  const SectionIn({required this.name, required this.lines});

  Map<String, dynamic> toJson() => {
        'name': name,
        'lines': lines.map((l) => l.toJson()).toList(),
      };

  factory SectionIn.fromJson(Map<String, dynamic> json) => SectionIn(
        name: json['name'] as String,
        lines: (json['lines'] as List)
            .map((l) => LineIn(
                  bars: (l['bars'] as List)
                      .map((b) => BarIn(
                            talaId: b['tala_id'] as String,
                            speed: b['speed'] as int? ?? 1,
                            swaras: b['swaras'] as List,
                            saahitya: List<String>.from(b['saahitya'] ?? []),
                          ))
                      .toList(),
                  repeat: l['repeat'] as int? ?? 2,
                ))
            .toList(),
      );
}

class Composition {
  final String? id;
  final String title;
  final String raga;
  final String talaId;
  final String composer;
  final double referenceSaHz;
  final List<SectionIn> sections;

  const Composition({
    this.id,
    required this.title,
    required this.raga,
    required this.talaId,
    this.composer = '',
    this.referenceSaHz = 261.63,
    this.sections = const [],
  });

  factory Composition.fromJson(Map<String, dynamic> json) => Composition(
        id: json['id'] as String?,
        title: json['title'] as String,
        raga: json['raga'] as String,
        talaId: json['tala_id'] as String,
        composer: json['composer'] as String? ?? '',
        referenceSaHz: (json['reference_sa_hz'] as num?)?.toDouble() ?? 261.63,
        sections: (json['sections'] as List?)
                ?.map(
                    (s) => SectionIn.fromJson(s as Map<String, dynamic>))
                .toList() ??
            [],
      );

  Map<String, dynamic> toJson() => {
        if (id != null) 'id': id,
        'title': title,
        'raga': raga,
        'tala_id': talaId,
        'composer': composer,
        'reference_sa_hz': referenceSaHz,
        'sections': sections.map((s) => s.toJson()).toList(),
      };
}
