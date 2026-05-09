import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/analysis_result.dart';
import '../models/swara.dart';
import '../services/api_client.dart';
import '../services/audio_service.dart';
import '../services/shruti_service.dart';
import '../theme/soundscape_theme.dart';
import '../widgets/raga_card.dart';
import '../widgets/sa_selector.dart';
import '../widgets/sa_suggestion_dialog.dart';
import '../widgets/script_selector.dart';
import '../widgets/swara_chip.dart';

class AnalysisScreen extends StatefulWidget {
  const AnalysisScreen({super.key});

  @override
  State<AnalysisScreen> createState() => _AnalysisScreenState();
}

class _AnalysisScreenState extends State<AnalysisScreen> {
  static const _saHzPrefKey = 'crj.analysis.reference_sa_hz';
  static const _shrutiPatternPrefKey = 'crj.analysis.shruti_pattern';
  static const _autoDetectSaPrefKey = 'crj.analysis.auto_detect_sa';
  static const _defaultSaHz = 261.63;
  static const _defaultShrutiPattern = 'sa_pa';

  String _algorithm = 'crepe';
  String _script = 'iast';
  bool _recording = false;
  bool _analyzing = false;
  AnalysisResult? _result;

  double _saHz = _defaultSaHz;
  List<TuningPreset> _presets = const [];

  String _shrutiPattern = _defaultShrutiPattern;
  bool _shrutiPlaying = false;
  bool _shrutiLoading = false;
  bool _autoDetectSa = true;

  late final ShrutiService _shruti;

  @override
  void initState() {
    super.initState();
    _shruti = ShrutiService(apiClient: context.read<ApiClient>());
    _shruti.playingStream.listen((p) {
      if (mounted) setState(() => _shrutiPlaying = p);
    });
    _loadSaPreference();
    _loadPresets();
  }

  @override
  void dispose() {
    _shruti.dispose();
    super.dispose();
  }

  Future<void> _loadSaPreference() async {
    final prefs = await SharedPreferences.getInstance();
    final storedSa = prefs.getDouble(_saHzPrefKey);
    final storedPattern = prefs.getString(_shrutiPatternPrefKey);
    final storedAuto = prefs.getBool(_autoDetectSaPrefKey);
    if (mounted) {
      setState(() {
        if (storedSa != null) _saHz = storedSa;
        if (storedPattern != null) _shrutiPattern = storedPattern;
        if (storedAuto != null) _autoDetectSa = storedAuto;
      });
    }
  }

  Future<void> _loadPresets() async {
    try {
      final api = context.read<ApiClient>();
      final presets = await api.getTuningPresets();
      if (mounted) setState(() => _presets = presets);
    } catch (_) {
      // Fall back to a hardcoded preset list if API is unreachable.
      if (mounted) {
        setState(() => _presets = const [
              TuningPreset(
                id: 'concert_a',
                description: 'A3',
                referenceSaHz: 220.0,
                westernReference: 'A3',
              ),
              TuningPreset(
                id: 'b_flat',
                description: 'Bb3',
                referenceSaHz: 233.08,
                westernReference: 'Bb3',
              ),
              TuningPreset(
                id: 'concert_c',
                description: 'C4',
                referenceSaHz: 261.63,
                westernReference: 'C4',
              ),
              TuningPreset(
                id: 'c_sharp',
                description: 'C#4',
                referenceSaHz: 277.18,
                westernReference: 'C#4',
              ),
              TuningPreset(
                id: 'd_sharp',
                description: 'D#4',
                referenceSaHz: 311.13,
                westernReference: 'D#4',
              ),
            ]);
      }
    }
  }

  Future<void> _setSaHz(double hz) async {
    setState(() => _saHz = hz);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble(_saHzPrefKey, hz);
    // If Shruti is playing, restart it at the new pitch.
    if (_shrutiPlaying) {
      try {
        await _shruti.play(saHz: hz, pattern: _shrutiPattern);
      } catch (_) {/* ignore — UI already shows current state */}
    }
  }

  Future<void> _setShrutiPattern(String pattern) async {
    setState(() => _shrutiPattern = pattern);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_shrutiPatternPrefKey, pattern);
    if (_shrutiPlaying) {
      try {
        await _shruti.play(saHz: _saHz, pattern: pattern);
      } catch (_) {/* ignore */}
    }
  }

  Future<void> _setAutoDetectSa(bool value) async {
    setState(() => _autoDetectSa = value);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_autoDetectSaPrefKey, value);
  }

  Future<void> _toggleShruti() async {
    if (_shrutiPlaying) {
      await _shruti.stop();
      return;
    }
    setState(() => _shrutiLoading = true);
    try {
      await _shruti.play(saHz: _saHz, pattern: _shrutiPattern);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Shruti error: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _shrutiLoading = false);
    }
  }

  Future<void> _startRecording() async {
    final audio = context.read<AudioService>();
    final ok = await audio.hasPermission();
    if (!ok) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Microphone permission required')),
        );
      }
      return;
    }
    // Fade out Shruti so it doesn't bleed into the recording.
    if (_shrutiPlaying) {
      await _shruti.fadeOutAndStop();
    }
    await audio.startRecording();
    setState(() => _recording = true);
  }

  Future<void> _stopRecording() async {
    final audio = context.read<AudioService>();
    final path = await audio.stopRecording();
    setState(() => _recording = false);
    if (path == null) return;

    final file = File(path);
    if (_autoDetectSa) {
      await _confirmSaThenAnalyze(file);
    } else {
      _analyze(file);
    }
  }

  Future<void> _confirmSaThenAnalyze(File file) async {
    setState(() => _analyzing = true);
    TonicSuggestion? suggestion;
    try {
      final api = context.read<ApiClient>();
      suggestion = await api.detectSa(file);
    } catch (e) {
      // Sa detection failure is non-fatal — fall back to current Sa.
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Sa detection skipped: $e')),
        );
      }
    }
    if (!mounted) return;
    setState(() => _analyzing = false);

    double saHzToUse = _saHz;
    if (suggestion != null) {
      final chosen = await showSaSuggestionDialog(
        context,
        suggestion: suggestion,
        currentSaHz: _saHz,
      );
      if (chosen != null) {
        await _setSaHz(chosen);
        saHzToUse = chosen;
      } else {
        return; // user dismissed without choosing
      }
    }
    await _analyze(file, overrideSaHz: saHzToUse);
  }

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.audio,
    );
    if (result == null || result.files.single.path == null) return;
    final file = File(result.files.single.path!);
    if (_autoDetectSa) {
      await _confirmSaThenAnalyze(file);
    } else {
      await _analyze(file);
    }
  }

  Future<void> _analyze(File file, {double? overrideSaHz}) async {
    setState(() => _analyzing = true);
    try {
      final api = context.read<ApiClient>();
      final r = await api.analyze(
        file,
        algorithm: _algorithm,
        script: _script,
        saHz: overrideSaHz ?? _saHz,
      );
      setState(() => _result = r);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Analysis error: $e'),
              backgroundColor: Colors.red),
        );
      }
    }
    if (mounted) setState(() => _analyzing = false);
  }

  Future<void> _exportText() async {
    if (_result == null) return;
    final r = _result!;
    final buf = StringBuffer()
      ..writeln('CRJ SoundScape Analysis Report')
      ..writeln('=' * 40)
      ..writeln('Duration: ${r.durationS.toStringAsFixed(2)}s')
      ..writeln('Algorithm: ${r.algorithm}')
      ..writeln('Reference Sa: ${r.referenceSaHz} Hz')
      ..writeln()
      ..writeln('Notation (IAST): ${r.notationIast}')
      ..writeln('Notation (Compact): ${r.notationCompact}')
      ..writeln()
      ..writeln('Unique Swaras: ${r.uniqueSwaras.join(", ")}');

    for (final rc in r.ragaCandidates) {
      buf.writeln(
          'Raga: ${rc.ragaName} — ${(rc.confidence * 100).toStringAsFixed(1)}%');
    }

    final dir = await getTemporaryDirectory();
    final file = File('${dir.path}/crj-analysis.txt');
    await file.writeAsString(buf.toString());
    await SharePlus.instance.share(ShareParams(files: [XFile(file.path)], text: 'CRJ Analysis Report'));
  }

  Future<void> _exportPdf() async {
    if (_result == null) return;
    try {
      final api = context.read<ApiClient>();
      final bytes = await api.exportPdf(_result!, script: _script);
      final dir = await getTemporaryDirectory();
      final file = File('${dir.path}/crj-analysis.pdf');
      await file.writeAsBytes(bytes);
      await SharePlus.instance.share(ShareParams(files: [XFile(file.path)], text: 'CRJ Analysis PDF'));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('PDF error: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('SWARA ANALYSIS')),
      body: _analyzing
          ? Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const CircularProgressIndicator(
                      color: SoundScapeTheme.amberGlow),
                  const SizedBox(height: 16),
                  Text('Analyzing audio...',
                      style: Theme.of(context).textTheme.bodyMedium),
                ],
              ),
            )
          : _result != null
              ? _buildResults()
              : _buildInput(),
    );
  }

  Widget _buildInput() {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Sa (tonic) selector
          _label('REFERENCE Sa'),
          const SizedBox(height: 8),
          if (_presets.isNotEmpty)
            SaSelector(
              selectedHz: _saHz,
              presets: _presets,
              onChanged: _setSaHz,
            )
          else
            Text(
              'Loading tuning presets…',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          const SizedBox(height: 16),

          // Shruti control
          _label('SHRUTI'),
          const SizedBox(height: 8),
          _buildShrutiRow(),
          const SizedBox(height: 16),

          // Auto-detect toggle
          Row(
            children: [
              Expanded(
                child: Text(
                  'Auto-detect Sa from recording',
                  style: GoogleFonts.cormorantGaramond(
                    fontSize: 14,
                    color: SoundScapeTheme.textLight,
                  ),
                ),
              ),
              Switch(
                value: _autoDetectSa,
                onChanged: _setAutoDetectSa,
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Algorithm selector
          _label('ALGORITHM'),
          const SizedBox(height: 8),
          Row(
            children: ['crepe', 'pyin'].map((a) {
              return Padding(
                padding: const EdgeInsets.only(right: 8),
                child: ChoiceChip(
                  label: Text(a.toUpperCase()),
                  selected: _algorithm == a,
                  onSelected: (_) => setState(() => _algorithm = a),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 20),

          // Script selector
          _label('SCRIPT'),
          const SizedBox(height: 8),
          ScriptSelector(
            selected: _script,
            onChanged: (s) => setState(() => _script = s),
          ),
          const SizedBox(height: 40),

          // Record button
          SizedBox(
            height: 50,
            child: ElevatedButton.icon(
              onPressed: _recording ? _stopRecording : _startRecording,
              icon: Icon(_recording ? Icons.stop_rounded : Icons.mic_rounded),
              label: Text(_recording ? 'STOP RECORDING' : 'RECORD'),
              style: _recording
                  ? ElevatedButton.styleFrom(
                      backgroundColor: SoundScapeTheme.lotusPink)
                  : null,
            ),
          ),
          const SizedBox(height: 16),

          // Upload button
          SizedBox(
            height: 50,
            child: OutlinedButton.icon(
              onPressed: _pickFile,
              icon: const Icon(Icons.upload_file_rounded),
              label: const Text('UPLOAD AUDIO FILE'),
            ),
          ),
          const SizedBox(height: 24),

          // Back to results if available
          if (_result != null)
            TextButton(
              onPressed: () => setState(() {}),
              child: const Text('View Previous Results'),
            ),
        ],
      ),
    );
  }

  Widget _buildResults() {
    final r = _result!;
    return DefaultTabController(
      length: 5,
      child: Column(
        children: [
          // Tab bar
          TabBar(
            isScrollable: true,
            labelColor: SoundScapeTheme.amberGlow,
            unselectedLabelColor: SoundScapeTheme.textMuted,
            indicatorColor: SoundScapeTheme.amberGlow,
            labelStyle: GoogleFonts.cinzel(fontSize: 10, letterSpacing: 1),
            tabs: const [
              Tab(text: 'SUMMARY'),
              Tab(text: 'NOTATION'),
              Tab(text: 'RAGAS'),
              Tab(text: 'PHRASES'),
              Tab(text: 'GAMAKAS'),
            ],
          ),
          // Export + New Analysis row
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              children: [
                OutlinedButton.icon(
                  onPressed: _exportText,
                  icon: const Icon(Icons.text_snippet_rounded, size: 16),
                  label: const Text('TEXT'),
                ),
                const SizedBox(width: 8),
                OutlinedButton.icon(
                  onPressed: _exportPdf,
                  icon: const Icon(Icons.picture_as_pdf_rounded, size: 16),
                  label: const Text('PDF'),
                ),
                const Spacer(),
                TextButton(
                  onPressed: () => setState(() => _result = null),
                  child: const Text('NEW'),
                ),
              ],
            ),
          ),
          // Tab content
          Expanded(
            child: TabBarView(
              children: [
                _summaryTab(r),
                _notationTab(r),
                _ragasTab(r),
                _phrasesTab(r),
                _gamakasTab(r),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _summaryTab(AnalysisResult r) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _infoRow('Duration', '${r.durationS.toStringAsFixed(2)} seconds'),
        _infoRow('Algorithm', r.algorithm.toUpperCase()),
        _infoRow('Reference Sa', '${r.referenceSaHz} Hz'),
        _infoRow('Script', r.script),
        _infoRow('Unique Swaras', '${r.uniqueSwaras.length}'),
        const SizedBox(height: 16),
        _label('SWARAS DETECTED'),
        const SizedBox(height: 8),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children:
              r.uniqueSwaras.map((s) => SwaraChip(label: s)).toList(),
        ),
        if (r.ragaCandidates.isNotEmpty) ...[
          const SizedBox(height: 20),
          _label('TOP RAGA'),
          const SizedBox(height: 8),
          RagaCard(raga: r.ragaCandidates.first, isTop: true),
        ],
      ],
    );
  }

  Widget _notationTab(AnalysisResult r) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _label('COMPACT'),
        const SizedBox(height: 8),
        _notationBox(r.notationCompact),
        const SizedBox(height: 20),
        _label('FULL (IAST)'),
        const SizedBox(height: 8),
        _notationBox(r.notationIast),
        if (r.notationRequested.isNotEmpty &&
            r.notationRequested != r.notationIast) ...[
          const SizedBox(height: 20),
          _label('REQUESTED SCRIPT'),
          const SizedBox(height: 8),
          _notationBox(r.notationRequested),
        ],
      ],
    );
  }

  Widget _ragasTab(AnalysisResult r) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        for (int i = 0; i < r.ragaCandidates.length; i++)
          RagaCard(raga: r.ragaCandidates[i], isTop: i == 0),
        if (r.ragaCandidates.isEmpty)
          Center(
            child: Text('No raga candidates identified',
                style: Theme.of(context).textTheme.bodyMedium),
          ),
      ],
    );
  }

  Widget _phrasesTab(AnalysisResult r) {
    return ListView.builder(
      padding: const EdgeInsets.all(20),
      itemCount: r.phrases.length,
      itemBuilder: (context, i) {
        final phrase = r.phrases[i];
        return Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: SoundScapeTheme.cardBg,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: SoundScapeTheme.cardBorder),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Phrase ${i + 1}  (${phrase.startMs.toInt()}–${phrase.endMs.toInt()} ms)',
                style: GoogleFonts.cinzel(
                  fontSize: 10,
                  letterSpacing: 1,
                  color: SoundScapeTheme.textMuted,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 4,
                runSpacing: 4,
                children: phrase.notes
                    .map((n) => SwaraChip(label: n.swaraId))
                    .toList(),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _gamakasTab(AnalysisResult r) {
    // Group gamakas by type
    final groups = <String, int>{};
    for (final g in r.gamakas) {
      groups[g.gamakaType] = (groups[g.gamakaType] ?? 0) + 1;
    }
    final entries = groups.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _label('GAMAKA TYPES DETECTED'),
        const SizedBox(height: 12),
        for (final e in entries)
          _infoRow(e.key, '${e.value} occurrences'),
        if (entries.isEmpty)
          Text('No gamakas detected',
              style: Theme.of(context).textTheme.bodyMedium),
      ],
    );
  }

  Widget _notationBox(String text) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: SoundScapeTheme.cardBg,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: SoundScapeTheme.cardBorder),
      ),
      child: SelectableText(
        text.isEmpty ? '—' : text,
        style: GoogleFonts.cormorantGaramond(
          fontSize: 16,
          height: 1.8,
          color: SoundScapeTheme.textLight,
        ),
      ),
    );
  }

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(label,
                style: GoogleFonts.cinzel(
                    fontSize: 10,
                    letterSpacing: 1,
                    color: SoundScapeTheme.textMuted)),
          ),
          Expanded(
            child: Text(value,
                style: GoogleFonts.cormorantGaramond(
                    fontSize: 14, color: SoundScapeTheme.textLight)),
          ),
        ],
      ),
    );
  }

  Widget _label(String text) => Text(
        text,
        style: GoogleFonts.cinzel(
          fontSize: 10,
          letterSpacing: 2,
          color: SoundScapeTheme.textMuted,
          fontWeight: FontWeight.w500,
        ),
      );

  Widget _buildShrutiRow() {
    const patterns = [
      ('sa_pa', 'Sa-Pa-Sa-Sa'),
      ('sa_ma', 'Sa-Ma-Sa-Sa'),
      ('sa_ni', 'Sa-Ni-Sa-Sa'),
    ];
    return Row(
      children: [
        Expanded(
          child: Wrap(
            spacing: 6,
            runSpacing: 6,
            children: patterns.map((p) {
              final isActive = p.$1 == _shrutiPattern;
              return GestureDetector(
                onTap: () => _setShrutiPattern(p.$1),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: isActive
                        ? SoundScapeTheme.amberGlow.withValues(alpha: 0.2)
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: isActive
                          ? SoundScapeTheme.amberGlow
                          : SoundScapeTheme.cardBorder,
                    ),
                  ),
                  child: Text(
                    p.$2,
                    style: GoogleFonts.cinzel(
                      fontSize: 10,
                      letterSpacing: 1,
                      color: isActive
                          ? SoundScapeTheme.amberGlow
                          : SoundScapeTheme.textLight,
                      fontWeight:
                          isActive ? FontWeight.w600 : FontWeight.w400,
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ),
        const SizedBox(width: 8),
        SizedBox(
          height: 36,
          child: ElevatedButton.icon(
            onPressed: _shrutiLoading ? null : _toggleShruti,
            icon: _shrutiLoading
                ? const SizedBox(
                    width: 14,
                    height: 14,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: SoundScapeTheme.deepSacred,
                    ),
                  )
                : Icon(
                    _shrutiPlaying
                        ? Icons.stop_rounded
                        : Icons.play_arrow_rounded,
                    size: 16,
                  ),
            label: Text(_shrutiPlaying ? 'STOP' : 'PLAY'),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 12),
            ),
          ),
        ),
      ],
    );
  }
}
