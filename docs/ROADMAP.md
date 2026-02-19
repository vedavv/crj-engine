# CRJ Engine — Development Roadmap

## Overview

The roadmap is organized into 3 major phases, with Phase 1 broken into weekly sprints.
Each phase builds on the previous one. MVP is the end of Phase 1.

---

## Phase 1: MVP — Carnatic Vocal Frequency Engine (Weeks 1–6)

**Goal**: Accept a vocal audio recording, detect pitch, map to Carnatic swaras with
multilingual output, and classify the top 3 gamaka types. Serve via web prototype.

### Sprint 1 (Week 1–2): Foundation & Pitch Detection

| Task | Description | Deliverable |
|------|-------------|-------------|
| 1.1 | Project scaffolding — pyproject.toml, CI, linting, test harness | Runnable empty project |
| 1.2 | Audio ingestion pipeline — load WAV/MP3, normalize, mono conversion | `crj_engine.pitch.audio_io` |
| 1.3 | CREPE pitch detection integration | `crj_engine.pitch.detector` |
| 1.4 | pYIN fallback detector via librosa | Same module, configurable |
| 1.5 | Pitch contour output format — `(timestamp, freq_hz, confidence)` | JSON + NumPy array output |
| 1.6 | Unit tests with synthetic tones (known frequencies) | 95%+ pass rate on sine waves |
| 1.7 | Test with `data/peer-test/audio/vkg.mp3` | Validated on real audio |

**Exit Criteria**: Given any WAV/MP3, produce a reliable F0 contour.

### Sprint 2 (Week 2–3): Swara Mapping & Multilingual Output

| Task | Description | Deliverable |
|------|-------------|-------------|
| 2.1 | Swarasthana JSON schema — 12 swaras × 5 scripts | `configs/swarasthanas.json` |
| 2.2 | Western note mapper (freq → note name + octave) | `crj_engine.swara.western` |
| 2.3 | Indian swara mapper (freq → swara, relative to Sa) | `crj_engine.swara.indian` |
| 2.4 | Configurable reference Sa (user sets their tonic) | Config parameter |
| 2.5 | Multilingual output renderer (Devanagari, Kannada, Tamil, Telugu, IAST) | `crj_engine.swara.transliterate` |
| 2.6 | Tolerance configuration (±10, ±25, ±50 cents) | Config parameter |
| 2.7 | Enharmonic candidate output (both valid names) | API response field |
| 2.8 | Integration test: full pipeline WAV → swara sequence | End-to-end test |

**Exit Criteria**: Given an F0 contour + reference Sa, output correct swara names in all 5 scripts.

### Sprint 3 (Week 3–4): Gamaka Classification (Top 3)

| Task | Description | Deliverable |
|------|-------------|-------------|
| 3.1 | Pitch contour windowing — extract 200-500ms segments | `crj_engine.pitch.segmenter` |
| 3.2 | Feature extraction — normalized contour + derivatives | Feature pipeline |
| 3.3 | Gamaka annotation format — JSON schema for training data | `configs/annotation_schema.json` |
| 3.4 | CNN-LSTM model architecture for gamaka classification | `crj_engine.pitch.gamaka` |
| 3.5 | Training script with synthetic gamaka curves | `scripts/train_gamaka.py` |
| 3.6 | Inference pipeline — contour → gamaka type + confidence | Model integration |
| 3.7 | Evaluation on held-out test set | >80% accuracy target |

**Exit Criteria**: Classify Kampita, Jaru, Sphuritham from vocal pitch contours.

### Sprint 4 (Week 4–5): Raga Identification (Rule-Based)

| Task | Description | Deliverable |
|------|-------------|-------------|
| 4.1 | Raga database — 72 Melakarta ragas in JSON | `configs/ragas/` |
| 4.2 | Arohana/Avarohana matching algorithm | `crj_engine.raga.matcher` |
| 4.3 | Swara set extraction from analysis output | Pipeline integration |
| 4.4 | Enharmonic disambiguation using raga context | Resolver logic |
| 4.5 | Ranked candidate output with confidence | API response |
| 4.6 | Test with known raga performances | Validation suite |

**Exit Criteria**: Given a swara sequence, correctly identify the Melakarta raga (>85% on test set).

### Sprint 5 (Week 5–6): API & Web Prototype

| Task | Description | Deliverable |
|------|-------------|-------------|
| 5.1 | FastAPI application skeleton | `crj_engine.api.main` |
| 5.2 | POST /analyze endpoint | Audio upload → full analysis |
| 5.3 | POST /identify-raga endpoint | Swara sequence → raga ID |
| 5.4 | GET /swarasthanas endpoint | Reference data API |
| 5.5 | GET /ragas endpoint | Raga database browser |
| 5.6 | Streamlit web prototype | Upload → visualize → results |
| 5.7 | Pitch contour visualization (matplotlib/plotly) | Visual output |
| 5.8 | Docker containerization | Dockerfile + compose |
| 5.9 | End-to-end integration tests | Full pipeline validation |

**Exit Criteria**: Working web app where a user can upload audio and see swara transcription
with gamaka annotations and raga identification.

---

## Phase 2: Expansion — Instruments + Hindustani (Weeks 7–14)

**Goal**: Support instrumental input (Veena, Violin, Flute), expand to Hindustani system,
add more gamaka types, introduce ML-based raga identification.

| Area | Key Tasks |
|------|-----------|
| Instruments | Instrument-aware pitch detection, harmonic separation |
| Hindustani | Hindustani raga database, thaat system, different gamaka vocabulary |
| Gamakas | Expand from 3 to 8-10 types (add Meend, Andolan, Murki, etc.) |
| Raga ML | Transformer-based raga classifier trained on labeled performances |
| Janya Ragas | Extend beyond 72 Melakarta to derived ragas |
| Batch Mode | Process multiple files, bulk transcription |
| Mobile API | Optimize API for mobile app consumption (CRJ Engine app) |

---

## Phase 3: Advanced — Sama Veda + Synthesis (Weeks 15–24)

**Goal**: Vedic chanting analysis and audio synthesis from notation.

| Area | Key Tasks |
|------|-----------|
| Sama Veda | Vedic swara recognition (Udaatta/Anudaatta/Svarita), corpus collection |
| Synthesis | Wavetable synthesis engine, instrument timbre modeling |
| Notation Editor | Interactive notation editor with playback |
| Advanced Viz | Pitch contour overlay on notation, real-time display |
| Production Deploy | AWS/GCP deployment, scaling, monitoring |
| Mobile App | CRJ Engine app integration (React Native) |

---

## Milestones & Decision Points

| Milestone | When | Decision |
|-----------|------|----------|
| Pitch detection validated | End of Sprint 1 | Confirm CREPE vs pYIN as default |
| Swara mapping complete | End of Sprint 2 | Review multilingual accuracy with experts |
| Gamaka model trained | End of Sprint 3 | Evaluate if synthetic training data suffices or need real annotations |
| MVP demo | End of Sprint 5 | Go/No-Go for Phase 2 expansion |
| Instrument support | End of Phase 2 | Assess need for polyphonic detection |
| Production readiness | End of Phase 3 | Cloud deployment architecture finalization |

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Insufficient annotated training data | High | Start with synthetic gamakas; partner with music institutions |
| CREPE accuracy on Indian microtones | Medium | Ensemble with pYIN; fine-tune CREPE on Carnatic data |
| Enharmonic disambiguation errors | Medium | Conservative: output both candidates; let user/raga context resolve |
| Compute costs for ML inference | Medium | Serverless architecture; model quantization; batch processing |
| Scope creep across 3 phases | High | Strict MVP boundary; weekly sprint reviews |

---

## Immediate Next Steps (This Week)

1. **Set up Python project** — pyproject.toml, virtual environment, dependencies
2. **Implement audio I/O** — load, normalize, convert MP3→WAV
3. **Integrate CREPE pitch detection** — run on `vkg.mp3` as first real test
4. **Create swarasthanas.json** — full 12-swara mapping with 5 scripts
5. **First passing test** — synthetic sine wave at known frequency maps to correct swara
