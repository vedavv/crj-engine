import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import '../models/swara.dart';
import '../models/tala.dart';
import '../services/api_client.dart';
import '../services/audio_service.dart';
import '../theme/soundscape_theme.dart';

class ComposerScreen extends StatefulWidget {
  const ComposerScreen({super.key});

  @override
  State<ComposerScreen> createState() => _ComposerScreenState();
}

class _ComposerScreenState extends State<ComposerScreen> {
  final _notationCtrl = TextEditingController(text: 'Sa Ri2 Ga3 Ma1 Pa');
  String _tone = 'voice';
  double _tempo = 60;
  int _speed = 1;
  bool _tanpura = false;
  bool _clickTrack = false;
  bool _useTala = false;
  String? _selectedTalaId;

  List<TuningPreset> _presets = [];
  List<Tala> _talas = [];
  TuningPreset? _selectedPreset;
  bool _loading = false;
  bool _generating = false;

  @override
  void initState() {
    super.initState();
    _loadReferenceData();
  }

  Future<void> _loadReferenceData() async {
    setState(() => _loading = true);
    final api = context.read<ApiClient>();
    try {
      final results = await Future.wait([
        api.getTuningPresets(),
        api.getTalas(),
      ]);
      setState(() {
        _presets = results[0] as List<TuningPreset>;
        _talas = results[1] as List<Tala>;
        if (_presets.isNotEmpty) _selectedPreset = _presets.first;
        if (_talas.isNotEmpty) _selectedTalaId = _talas[11].id; // Adi Tala
      });
    } catch (e) {
      // Use defaults
    }
    setState(() => _loading = false);
  }

  Future<void> _generate() async {
    if (_notationCtrl.text.trim().isEmpty) return;
    setState(() => _generating = true);
    try {
      final api = context.read<ApiClient>();
      final audio = context.read<AudioService>();
      final wav = await api.compose(
        _notationCtrl.text.trim(),
        tone: _tone,
        tempoBpm: _tempo,
        speed: _speed,
        talaId: _useTala ? _selectedTalaId : null,
        tanpura: _tanpura,
        clickTrack: _clickTrack,
      );
      await audio.playBytes(wav);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
        );
      }
    }
    if (mounted) setState(() => _generating = false);
  }

  @override
  void dispose() {
    _notationCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('NOTATION COMPOSER')),
      body: _loading
          ? const Center(
              child:
                  CircularProgressIndicator(color: SoundScapeTheme.amberGlow))
          : ListView(
              padding: const EdgeInsets.all(20),
              children: [
                // Notation input
                _sectionLabel('NOTATION'),
                const SizedBox(height: 8),
                TextField(
                  controller: _notationCtrl,
                  style: GoogleFonts.cormorantGaramond(
                    fontSize: 18,
                    color: SoundScapeTheme.textLight,
                    height: 1.6,
                  ),
                  maxLines: 4,
                  decoration: InputDecoration(
                    hintText: 'e.g. Sa Ri2 Ga3 Ma1 Pa Dha2 Ni3 Sa+',
                    hintStyle: GoogleFonts.cormorantGaramond(
                      fontSize: 16,
                      color: SoundScapeTheme.textMuted,
                    ),
                    filled: true,
                    fillColor: SoundScapeTheme.cardBg,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide:
                          const BorderSide(color: SoundScapeTheme.cardBorder),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide:
                          const BorderSide(color: SoundScapeTheme.cardBorder),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide:
                          const BorderSide(color: SoundScapeTheme.amberGlow),
                    ),
                  ),
                ),
                const SizedBox(height: 20),

                // Instrument
                _sectionLabel('INSTRUMENT'),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: ['voice', 'string', 'flute', 'sine']
                      .map((t) => ChoiceChip(
                            label: Text(t[0].toUpperCase() + t.substring(1)),
                            selected: _tone == t,
                            onSelected: (_) => setState(() => _tone = t),
                          ))
                      .toList(),
                ),
                const SizedBox(height: 20),

                // Sa pitch
                if (_presets.isNotEmpty) ...[
                  _sectionLabel('SA PITCH'),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    decoration: BoxDecoration(
                      color: SoundScapeTheme.cardBg,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: SoundScapeTheme.cardBorder),
                    ),
                    child: DropdownButton<TuningPreset>(
                      value: _selectedPreset,
                      isExpanded: true,
                      dropdownColor: SoundScapeTheme.cardBg,
                      underline: const SizedBox(),
                      style: GoogleFonts.cormorantGaramond(
                        fontSize: 14,
                        color: SoundScapeTheme.textLight,
                      ),
                      items: _presets
                          .map((p) => DropdownMenuItem(
                                value: p,
                                child: Text(p.description),
                              ))
                          .toList(),
                      onChanged: (p) => setState(() => _selectedPreset = p),
                    ),
                  ),
                  const SizedBox(height: 20),
                ],

                // Speed
                _sectionLabel('SPEED'),
                const SizedBox(height: 8),
                Row(
                  children: [1, 2, 3].map((s) {
                    final active = _speed == s;
                    return Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        label: Text('${s}x'),
                        selected: active,
                        onSelected: (_) => setState(() => _speed = s),
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 20),

                // Tempo
                _sectionLabel('TEMPO: ${_tempo.toInt()} BPM'),
                Slider(
                  value: _tempo,
                  min: 30,
                  max: 240,
                  divisions: 42,
                  label: '${_tempo.toInt()}',
                  onChanged: (v) => setState(() => _tempo = v),
                ),
                const SizedBox(height: 12),

                // Tala toggle + selector
                Row(
                  children: [
                    Switch(
                      value: _useTala,
                      onChanged: (v) => setState(() => _useTala = v),
                    ),
                    const SizedBox(width: 8),
                    _sectionLabel('TALA'),
                  ],
                ),
                if (_useTala && _talas.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    decoration: BoxDecoration(
                      color: SoundScapeTheme.cardBg,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: SoundScapeTheme.cardBorder),
                    ),
                    child: DropdownButton<String>(
                      value: _selectedTalaId,
                      isExpanded: true,
                      dropdownColor: SoundScapeTheme.cardBg,
                      underline: const SizedBox(),
                      style: GoogleFonts.cormorantGaramond(
                        fontSize: 14,
                        color: SoundScapeTheme.textLight,
                      ),
                      items: _talas
                          .map((t) => DropdownMenuItem(
                                value: t.id,
                                child: Text(
                                    '${t.name} (${t.totalAksharas} aksharas)'),
                              ))
                          .toList(),
                      onChanged: (id) =>
                          setState(() => _selectedTalaId = id),
                    ),
                  ),
                ],
                const SizedBox(height: 16),

                // Toggles
                Row(
                  children: [
                    Switch(
                      value: _clickTrack,
                      onChanged: (v) => setState(() => _clickTrack = v),
                    ),
                    const SizedBox(width: 4),
                    Text('Click Track',
                        style: Theme.of(context).textTheme.labelLarge),
                    const SizedBox(width: 20),
                    Switch(
                      value: _tanpura,
                      onChanged: (v) => setState(() => _tanpura = v),
                    ),
                    const SizedBox(width: 4),
                    Text('Shruti Drone',
                        style: Theme.of(context).textTheme.labelLarge),
                  ],
                ),
                const SizedBox(height: 24),

                // Generate button
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: ElevatedButton.icon(
                    onPressed: _generating ? null : _generate,
                    icon: _generating
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: SoundScapeTheme.deepSacred,
                            ),
                          )
                        : const Icon(Icons.play_arrow_rounded),
                    label: Text(_generating ? 'GENERATING...' : 'GENERATE & PLAY'),
                  ),
                ),
                const SizedBox(height: 24),
              ],
            ),
    );
  }

  Widget _sectionLabel(String text) => Text(
        text,
        style: GoogleFonts.cinzel(
          fontSize: 10,
          letterSpacing: 2,
          color: SoundScapeTheme.textMuted,
          fontWeight: FontWeight.w500,
        ),
      );
}
