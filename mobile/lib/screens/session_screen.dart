import 'dart:io';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/analysis_result.dart';
import '../models/swara.dart';
import '../services/api_client.dart';
import '../services/audio_service.dart';
import '../services/shruti_service.dart';
import '../services/tala_service.dart';
import '../theme/soundscape_theme.dart';
import '../widgets/raga_card.dart';
import '../widgets/sa_selector.dart';
import '../widgets/sa_suggestion_dialog.dart';
import '../widgets/swara_chip.dart';
import '../widgets/tala_selector.dart';

/// Practice / performance session: Shruti + Tala running together while
/// the user sings or plays. Optional mic recording can be analysed in-place
/// via /detect-sa + /analyze.
class SessionScreen extends StatefulWidget {
  const SessionScreen({super.key});

  @override
  State<SessionScreen> createState() => _SessionScreenState();
}

class _SessionScreenState extends State<SessionScreen> {
  // Shared SharedPreferences keys with AnalysisScreen so settings carry over
  static const _saHzPrefKey = 'crj.analysis.reference_sa_hz';
  static const _shrutiPatternPrefKey = 'crj.analysis.shruti_pattern';
  static const _talaIdPrefKey = 'crj.analysis.tala_id';
  static const _talaInstrumentPrefKey = 'crj.analysis.tala_instrument';
  static const _talaTempoPrefKey = 'crj.analysis.tala_tempo';

  static const _defaultSaHz = 261.63;
  static const _defaultShrutiPattern = 'sa_pa';
  static const _defaultTalaId = 'triputa_chatusra';
  static const _defaultTalaInstrument = 'mridangam';
  static const _defaultTempoBpm = 80;

  double _saHz = _defaultSaHz;
  List<TuningPreset> _presets = const [];
  String _shrutiPattern = _defaultShrutiPattern;
  String _talaId = _defaultTalaId;
  String _talaInstrument = _defaultTalaInstrument;
  int _tempoBpm = _defaultTempoBpm;

  bool _shrutiPlaying = false;
  bool _talaPlaying = false;
  bool _shrutiLoading = false;
  bool _talaLoading = false;

  bool _recording = false;
  bool _analyzing = false;
  String? _lastRecordingPath;

  ShrutiService get _shruti => context.read<ShrutiService>();
  TalaService get _tala => context.read<TalaService>();

  @override
  void initState() {
    super.initState();
    // Listen for state changes after first frame so Provider context is ready.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _shruti.playingStream.listen((p) {
        if (mounted) setState(() => _shrutiPlaying = p);
      });
      _tala.playingStream.listen((p) {
        if (mounted) setState(() => _talaPlaying = p);
      });
      // Sync initial play state
      setState(() {
        _shrutiPlaying = _shruti.isPlaying;
        _talaPlaying = _tala.isPlaying;
      });
    });
    _loadPreferences();
    _loadPresets();
  }

  Future<void> _loadPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;
    setState(() {
      _saHz = prefs.getDouble(_saHzPrefKey) ?? _defaultSaHz;
      _shrutiPattern =
          prefs.getString(_shrutiPatternPrefKey) ?? _defaultShrutiPattern;
      _talaId = prefs.getString(_talaIdPrefKey) ?? _defaultTalaId;
      _talaInstrument =
          prefs.getString(_talaInstrumentPrefKey) ?? _defaultTalaInstrument;
      _tempoBpm = prefs.getInt(_talaTempoPrefKey) ?? _defaultTempoBpm;
    });
  }

  Future<void> _loadPresets() async {
    try {
      final api = context.read<ApiClient>();
      final presets = await api.getTuningPresets();
      if (mounted) setState(() => _presets = presets);
    } catch (_) {/* fallback presets handled in SaSelector if empty */}
  }

  // ── Setters with persistence ─────────────────────────────────────────

  Future<void> _setSaHz(double hz) async {
    setState(() => _saHz = hz);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble(_saHzPrefKey, hz);
    if (_shrutiPlaying) {
      try {
        await _shruti.play(saHz: hz, pattern: _shrutiPattern);
      } catch (_) {}
    }
  }

  Future<void> _setShrutiPattern(String p) async {
    setState(() => _shrutiPattern = p);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_shrutiPatternPrefKey, p);
    if (_shrutiPlaying) {
      try {
        await _shruti.play(saHz: _saHz, pattern: p);
      } catch (_) {}
    }
  }

  Future<void> _setTalaId(String id) async {
    setState(() => _talaId = id);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_talaIdPrefKey, id);
    if (_talaPlaying) {
      try {
        await _tala.play(
          talaId: id,
          instrument: _talaInstrument,
          tempoBpm: _tempoBpm,
        );
      } catch (_) {}
    }
  }

  Future<void> _setTalaInstrument(String inst) async {
    setState(() => _talaInstrument = inst);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_talaInstrumentPrefKey, inst);
    if (_talaPlaying) {
      try {
        await _tala.play(
          talaId: _talaId,
          instrument: inst,
          tempoBpm: _tempoBpm,
        );
      } catch (_) {}
    }
  }

  Future<void> _setTempo(int bpm) async {
    setState(() => _tempoBpm = bpm);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_talaTempoPrefKey, bpm);
  }

  // ── Playback controls ────────────────────────────────────────────────

  Future<void> _toggleShruti() async {
    if (_shrutiPlaying) {
      await _shruti.stop();
      return;
    }
    setState(() => _shrutiLoading = true);
    try {
      await _shruti.play(saHz: _saHz, pattern: _shrutiPattern);
    } catch (e) {
      _showSnack('Shruti error: $e');
    } finally {
      if (mounted) setState(() => _shrutiLoading = false);
    }
  }

  Future<void> _toggleTala() async {
    if (_talaPlaying) {
      await _tala.stop();
      return;
    }
    setState(() => _talaLoading = true);
    try {
      await _tala.play(
        talaId: _talaId,
        instrument: _talaInstrument,
        tempoBpm: _tempoBpm,
      );
    } catch (e) {
      _showSnack('Tala error: $e');
    } finally {
      if (mounted) setState(() => _talaLoading = false);
    }
  }

  Future<void> _playAll() async {
    setState(() {
      _shrutiLoading = true;
      _talaLoading = true;
    });
    try {
      // Fire both fetches in parallel; whichever cache-hits plays first
      await Future.wait([
        _shruti.play(saHz: _saHz, pattern: _shrutiPattern),
        _tala.play(
          talaId: _talaId,
          instrument: _talaInstrument,
          tempoBpm: _tempoBpm,
        ),
      ]);
    } catch (e) {
      _showSnack('Accompaniment error: $e');
    } finally {
      if (mounted) {
        setState(() {
          _shrutiLoading = false;
          _talaLoading = false;
        });
      }
    }
  }

  Future<void> _stopAll() async {
    await Future.wait([_shruti.stop(), _tala.stop()]);
  }

  // ── Recording ────────────────────────────────────────────────────────
  // Mic-only — accompaniment keeps playing through speakers/headphones so the
  // user can practice along. The recorded file contains only the mic input
  // (the OS doesn't capture system audio on iOS by default), so analysis
  // pipelines see clean voice without backing tracks.

  Future<void> _startRecording() async {
    final audio = context.read<AudioService>();
    final ok = await audio.hasPermission();
    if (!ok) {
      _showSnack('Microphone permission required');
      return;
    }
    await audio.startRecording();
    setState(() => _recording = true);
  }

  Future<void> _stopRecording() async {
    final audio = context.read<AudioService>();
    final path = await audio.stopRecording();
    setState(() {
      _recording = false;
      _lastRecordingPath = path;
    });
  }

  Future<void> _analyzeRecording() async {
    final path = _lastRecordingPath;
    if (path == null) return;
    setState(() => _analyzing = true);

    final api = context.read<ApiClient>();
    final file = File(path);
    double saHzToUse = _saHz;

    // Optional Sa auto-detect on the captured voice
    try {
      final suggestion = await api.detectSa(file);
      if (!mounted) return;
      final chosen = await showSaSuggestionDialog(
        context,
        suggestion: suggestion,
        currentSaHz: _saHz,
      );
      if (chosen == null) {
        setState(() => _analyzing = false);
        return;
      }
      await _setSaHz(chosen);
      saHzToUse = chosen;
    } catch (_) {
      // Detection failure is non-fatal — fall through with current Sa
    }

    try {
      final result = await api.analyze(
        file,
        algorithm: 'crepe',
        script: 'iast',
        saHz: saHzToUse,
      );
      if (!mounted) return;
      _showResultSheet(result);
    } catch (e) {
      _showSnack('Analysis error: $e');
    } finally {
      if (mounted) setState(() => _analyzing = false);
    }
  }

  void _showResultSheet(AnalysisResult r) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: SoundScapeTheme.cardBg,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) => SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxHeight: MediaQuery.of(ctx).size.height * 0.75,
          ),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Center(
                  child: Container(
                    width: 36,
                    height: 4,
                    decoration: BoxDecoration(
                      color: SoundScapeTheme.cardBorder,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  'SESSION ANALYSIS',
                  style: GoogleFonts.cinzel(
                    fontSize: 13,
                    letterSpacing: 2,
                    color: SoundScapeTheme.amberGlow,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                _summaryRow(
                  'Duration', '${r.durationS.toStringAsFixed(2)} s'),
                _summaryRow(
                    'Reference Sa', '${r.referenceSaHz} Hz'),
                _summaryRow(
                    'Unique Swaras', '${r.uniqueSwaras.length}'),
                const SizedBox(height: 12),
                if (r.uniqueSwaras.isNotEmpty) ...[
                  _label('SWARAS DETECTED'),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: r.uniqueSwaras
                        .map((s) => SwaraChip(label: s))
                        .toList(),
                  ),
                  const SizedBox(height: 14),
                ],
                if (r.notationCompact.isNotEmpty) ...[
                  _label('NOTATION'),
                  const SizedBox(height: 6),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: SoundScapeTheme.deepSacred,
                      borderRadius: BorderRadius.circular(6),
                      border:
                          Border.all(color: SoundScapeTheme.cardBorder),
                    ),
                    child: SelectableText(
                      r.notationCompact,
                      style: GoogleFonts.cormorantGaramond(
                        fontSize: 14,
                        height: 1.7,
                        color: SoundScapeTheme.textLight,
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),
                ],
                if (r.ragaCandidates.isNotEmpty) ...[
                  _label('TOP RAGA'),
                  const SizedBox(height: 6),
                  RagaCard(
                    raga: r.ragaCandidates.first,
                    isTop: true,
                  ),
                ],
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () => Navigator.of(ctx).pop(),
                  child: const Text('CONTINUE SESSION'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _summaryRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          SizedBox(
            width: 110,
            child: Text(
              label,
              style: GoogleFonts.cinzel(
                fontSize: 9,
                letterSpacing: 1.5,
                color: SoundScapeTheme.textMuted,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: GoogleFonts.cormorantGaramond(
                fontSize: 14,
                color: SoundScapeTheme.textLight,
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _discardRecording() {
    setState(() => _lastRecordingPath = null);
  }

  void _showSnack(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  // ── UI ───────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('SESSION')),
      body: _analyzing
          ? const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  CircularProgressIndicator(color: SoundScapeTheme.amberGlow),
                  SizedBox(height: 16),
                  Text('Analysing recording…'),
                ],
              ),
            )
          : SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _label('REFERENCE Sa'),
                  const SizedBox(height: 8),
                  if (_presets.isNotEmpty)
                    SaSelector(
                      selectedHz: _saHz,
                      presets: _presets,
                      onChanged: _setSaHz,
                    )
                  else
                    Text('Loading…',
                        style: Theme.of(context).textTheme.bodyMedium),
                  const SizedBox(height: 20),

                  // Shruti
                  Row(
                    children: [
                      Expanded(child: _label('SHRUTI')),
                      _miniPlayButton(
                        playing: _shrutiPlaying,
                        loading: _shrutiLoading,
                        onPressed: _toggleShruti,
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  _shrutiPatternRow(),
                  const SizedBox(height: 20),

                  // Tala
                  Row(
                    children: [
                      Expanded(child: _label('TALA')),
                      _miniPlayButton(
                        playing: _talaPlaying,
                        loading: _talaLoading,
                        onPressed: _toggleTala,
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  TalaSelector(
                    selectedTalaId: _talaId,
                    selectedInstrument: _talaInstrument,
                    tempoBpm: _tempoBpm,
                    onTalaChanged: _setTalaId,
                    onInstrumentChanged: _setTalaInstrument,
                    onTempoChanged: _setTempo,
                  ),
                  const SizedBox(height: 24),

                  // Big PLAY ALL / STOP ALL button
                  SizedBox(
                    height: 56,
                    child: ElevatedButton.icon(
                      onPressed: (_shrutiPlaying || _talaPlaying)
                          ? _stopAll
                          : _playAll,
                      icon: Icon(
                        (_shrutiPlaying || _talaPlaying)
                            ? Icons.stop_rounded
                            : Icons.play_arrow_rounded,
                        size: 22,
                      ),
                      label: Text(
                        (_shrutiPlaying || _talaPlaying)
                            ? 'STOP ACCOMPANIMENT'
                            : 'PLAY ACCOMPANIMENT',
                      ),
                    ),
                  ),

                  // Tip about earphones
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: SoundScapeTheme.cardBg,
                      borderRadius: BorderRadius.circular(6),
                      border:
                          Border.all(color: SoundScapeTheme.cardBorder),
                    ),
                    child: Row(
                      children: [
                        const Icon(
                          Icons.headset_rounded,
                          color: SoundScapeTheme.textMuted,
                          size: 18,
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            'Use earphones for cleanest mic capture. '
                            'Speaker accompaniment can leak into the mic '
                            'and reduce analysis accuracy.',
                            style: GoogleFonts.cormorantGaramond(
                              fontSize: 12,
                              color: SoundScapeTheme.textMuted,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                  const Divider(height: 32),

                  // Recording controls
                  _label('RECORDING'),
                  const SizedBox(height: 8),
                  if (_recording)
                    SizedBox(
                      height: 50,
                      child: ElevatedButton.icon(
                        onPressed: _stopRecording,
                        icon: const Icon(Icons.stop_rounded),
                        label: const Text('STOP RECORDING'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: SoundScapeTheme.lotusPink,
                        ),
                      ),
                    )
                  else
                    SizedBox(
                      height: 50,
                      child: ElevatedButton.icon(
                        onPressed: _startRecording,
                        icon: const Icon(Icons.fiber_manual_record_rounded),
                        label: Text(
                          _lastRecordingPath == null
                              ? 'START RECORDING'
                              : 'RECORD AGAIN',
                        ),
                      ),
                    ),

                  if (_lastRecordingPath != null && !_recording) ...[
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: _analyzeRecording,
                            icon: const Icon(Icons.graphic_eq_rounded,
                                size: 16),
                            label: const Text('ANALYSE'),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: _discardRecording,
                            icon: const Icon(Icons.delete_outline_rounded,
                                size: 16),
                            label: const Text('DISCARD'),
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
    );
  }

  // ── Helpers ──────────────────────────────────────────────────────────

  Widget _label(String text) => Text(
        text,
        style: GoogleFonts.cinzel(
          fontSize: 10,
          letterSpacing: 2,
          color: SoundScapeTheme.textMuted,
          fontWeight: FontWeight.w500,
        ),
      );

  Widget _miniPlayButton({
    required bool playing,
    required bool loading,
    required VoidCallback onPressed,
  }) {
    return SizedBox(
      height: 32,
      child: ElevatedButton.icon(
        onPressed: loading ? null : onPressed,
        icon: loading
            ? const SizedBox(
                width: 12,
                height: 12,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: SoundScapeTheme.deepSacred,
                ),
              )
            : Icon(
                playing ? Icons.stop_rounded : Icons.play_arrow_rounded,
                size: 14,
              ),
        label: Text(playing ? 'STOP' : 'PLAY'),
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 10),
        ),
      ),
    );
  }

  Widget _shrutiPatternRow() {
    const patterns = [
      ('sa_pa', 'Sa-Pa-Sa-Sa'),
      ('sa_ma', 'Sa-Ma-Sa-Sa'),
      ('sa_ni', 'Sa-Ni-Sa-Sa'),
    ];
    return Wrap(
      spacing: 6,
      runSpacing: 6,
      children: patterns.map((p) {
        final active = p.$1 == _shrutiPattern;
        return GestureDetector(
          onTap: () => _setShrutiPattern(p.$1),
          child: Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: active
                  ? SoundScapeTheme.amberGlow.withValues(alpha: 0.2)
                  : Colors.transparent,
              borderRadius: BorderRadius.circular(4),
              border: Border.all(
                color: active
                    ? SoundScapeTheme.amberGlow
                    : SoundScapeTheme.cardBorder,
              ),
            ),
            child: Text(
              p.$2,
              style: GoogleFonts.cinzel(
                fontSize: 10,
                letterSpacing: 1,
                color: active
                    ? SoundScapeTheme.amberGlow
                    : SoundScapeTheme.textLight,
                fontWeight: active ? FontWeight.w600 : FontWeight.w400,
              ),
            ),
          ),
        );
      }).toList(),
    );
  }
}
