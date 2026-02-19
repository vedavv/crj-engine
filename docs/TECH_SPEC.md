# CRJ Engine — Technology Specification

## 1. System Overview

CRJ Engine is the core audio-intelligence backend for CRJ Studio. It performs:

1. **Pitch Detection** — Extract fundamental frequency (F0) contours from audio
2. **Swara Mapping** — Convert frequencies to Indian classical swarasthanas with multilingual output
3. **Gamaka Classification** — Identify ornamental pitch movements (Kampita, Jaru, Sphuritham, Meend, etc.)
4. **Raga Identification** — Classify the melodic framework from swara sequences
5. **Sama Veda Analysis** — Recognize Vedic chanting swaras (Udaatta, Anudaatta, Svarita)
6. **Synthesis** — Render notation back to audio with instrument-specific timbres

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                          │
│   Mobile App (React Native)  │  Web UI (Streamlit)      │
└──────────────┬──────────────────────────┬───────────────┘
               │ REST/WebSocket           │ HTTP
┌──────────────▼──────────────────────────▼───────────────┐
│                    API LAYER (FastAPI)                    │
│   /analyze  /transcribe  /identify-raga  /synthesize     │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│                  PROCESSING PIPELINE                     │
│                                                          │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌────────┐ │
│  │  Pitch   │→ │   Swara   │→ │  Gamaka  │→ │  Raga  │ │
│  │Detection │  │  Mapping  │  │ Classify │  │  ID    │ │
│  └──────────┘  └───────────┘  └──────────┘  └────────┘ │
│       │                                          │       │
│       ▼                                          ▼       │
│  ┌──────────┐                             ┌──────────┐  │
│  │Synthesis │                             │Sama Veda │  │
│  │ Engine   │                             │ Analyzer │  │
│  └──────────┘                             └──────────┘  │
└─────────────────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│                    DATA LAYER                            │
│   PostgreSQL  │  File Storage  │  Model Registry         │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Component Specifications

### 3.1 Pitch Detection Module (`src/crj_engine/pitch/`)

**Purpose**: Extract F0 (fundamental frequency) contour from audio input.

**Algorithms** (configurable, used in ensemble or standalone):

| Algorithm | Library    | Strengths                         | Use Case              |
|-----------|------------|-----------------------------------|-----------------------|
| CREPE     | crepe/torchcrepe | Best accuracy, noise-robust | Primary detector      |
| pYIN      | librosa    | Fast, good for clean audio        | Fallback / validation |
| Essentia  | essentia   | Melodia algorithm, polyphonic     | Instrument separation |
| Aubio     | aubio      | Low latency, real-time capable    | Live monitoring       |

**Input**: WAV/MP3 audio (mono preferred, auto-converted if stereo)
**Output**: Time-series of `(timestamp_ms, frequency_hz, confidence)` tuples
**Sample Rate**: 16kHz for pitch detection (downsampled from source)
**Frame Size**: 10ms hop (configurable)

**Key Design Decisions**:
- CREPE is the default detector — it handles microtonal intervals critical for gamakas
- Ensemble mode averages CREPE + pYIN with confidence weighting for higher accuracy
- Silence detection threshold: -40 dB RMS (configurable)

### 3.2 Swara Mapping Module (`src/crj_engine/swara/`)

**Purpose**: Convert Hz frequencies to swarasthanas in both Western and Indian systems.

**Western Mapping** (absolute, A4 = 440 Hz):
```
note_number = 12 * log2(freq / 440) + 69
note_name = ["C", "C#", "D", ...][note_number % 12]
octave = (note_number // 12) - 1
```

**Indian Mapping** (relative to Shadja):
```
cents_from_sa = 1200 * log2(freq / reference_sa_hz)
swarasthana = lookup(cents_from_sa, tolerance=25_cents)
```

**The 12 Swarasthanas** (with cent values from Sa):

| # | Swara     | Cents | Western Equiv | Devanagari | Kannada | Tamil  | Telugu |
|---|-----------|-------|---------------|------------|---------|--------|--------|
| 1 | Sa        | 0     | C (tonic)     | स          | ಸ       | ச      | స      |
| 2 | Ri₁       | 100   | C#/Db         | रि₁       | ರಿ₁     | ரி₁    | రి₁    |
| 3 | Ri₂/Ga₁   | 200   | D             | रि₂       | ರಿ₂     | ரி₂    | రి₂    |
| 4 | Ga₂/Ri₃   | 300   | D#/Eb         | ग₂        | ಗ₂      | க₂     | గ₂     |
| 5 | Ga₃       | 400   | E             | ग₃        | ಗ₃      | க₃     | గ₃     |
| 6 | Ma₁       | 500   | F             | म₁        | ಮ₁      | ம₁     | మ₁     |
| 7 | Ma₂       | 600   | F#/Gb         | म₂        | ಮ₂      | ம₂     | మ₂     |
| 8 | Pa        | 700   | G             | प          | ಪ       | ப      | ప      |
| 9 | Dha₁      | 800   | G#/Ab         | ध₁        | ಧ₁      | த₁     | ధ₁     |
|10 | Dha₂/Ni₁  | 900   | A             | ध₂        | ಧ₂      | த₂     | ధ₂     |
|11 | Ni₂/Dha₃  | 1000  | A#/Bb         | नि₂       | ನಿ₂     | நி₂    | ని₂    |
|12 | Ni₃       | 1100  | B             | नि₃       | ನಿ₃     | நி₃    | ని₃    |

**Enharmonic Disambiguation**: When a frequency maps to a position that has two
valid swara names (e.g., Ri₂ vs Ga₁ at 200 cents), the correct name depends on
the Raga context. The swara module outputs both candidates; the Raga module resolves.

**Tolerance**: Default ±25 cents (half a semitone). Configurable for stricter
śruti-level precision (±10 cents) or looser beginner mode (±50 cents).

### 3.3 Gamaka Classification Module (`src/crj_engine/pitch/gamaka.py`)

**Purpose**: Classify ornamental pitch movements from F0 contours.

**MVP Gamaka Types (Phase 1)**:

| Gamaka      | Description                          | Pitch Signature              |
|-------------|--------------------------------------|------------------------------|
| Kampita     | Oscillation around a note            | Periodic vibrato-like curve  |
| Jaru        | Smooth glide between two notes       | Monotonic pitch slide        |
| Sphuritham  | Quick touch of adjacent note         | Brief spike then return      |

**Approach**: CNN-LSTM on short (200-500ms) windowed pitch contour segments.
- Input: Normalized pitch contour (cents from Sa) + first derivative
- Output: Gamaka type + confidence score
- Training data: Expert-annotated segments from Carnatic vocal recordings

### 3.4 Raga Identification Module (`src/crj_engine/raga/`)

**Purpose**: Identify the Raga from a sequence of detected swaras.

**Approach (phased)**:
- **Phase 1 (Rule-based)**: Arohana/Avarohana matching against a Raga database.
  Compare detected swara set with known Raga definitions. Handles top 72 Melakarta ragas.
- **Phase 2 (ML)**: Transformer-based sequence classifier trained on labeled
  performances. Handles Janya ragas and ambiguous cases.

**Raga Database**: JSON files in `configs/ragas/` with structure:
```json
{
  "name": "Shankarabharanam",
  "melakarta_number": 29,
  "arohana": ["Sa", "Ri2", "Ga3", "Ma1", "Pa", "Dha2", "Ni3", "Sa"],
  "avarohana": ["Sa", "Ni3", "Dha2", "Pa", "Ma1", "Ga3", "Ri2", "Sa"],
  "characteristic_phrases": ["Ri2-Ga3-Ma1-Pa", "Dha2-Ni3-Sa"],
  "aliases": {"kannada": "ಶಂಕರಾಭರಣಂ", "devanagari": "शंकराभरणं"}
}
```

### 3.5 Sama Veda Analyzer (`src/crj_engine/swara/vedic.py`)

**Purpose**: Recognize Vedic chanting pitch accents.

**Vedic Swaras**:
| Swara     | Meaning       | Pitch Level |
|-----------|---------------|-------------|
| Udaatta   | Raised        | High        |
| Anudaatta | Not raised    | Low         |
| Svarita   | Sounded       | Falling     |

**Phase 3 feature** — requires specialized corpus of 20+ hours annotated chanting.

### 3.6 Synthesis Engine (`src/crj_engine/synthesis/`)

**Purpose**: Render notation back to audio with realistic instrument timbres.

**Phase 3 feature** — requires high-fidelity instrument samples (96-192kHz).
Initial approach: Wavetable synthesis with gamaka-aware pitch envelope shaping.

---

## 4. Technology Stack — Final Choices & Rationale

### 4.1 Core Language: Python 3.11+
- Richest audio/ML ecosystem (librosa, PyTorch, Essentia all Python-native)
- Fast prototyping critical for research-heavy project
- Performance-sensitive paths can use NumPy/C extensions

### 4.2 Audio Processing
| Library      | Version | Purpose                              |
|-------------|---------|--------------------------------------|
| librosa     | ≥0.10   | Feature extraction, pYIN pitch       |
| torchcrepe  | ≥0.0.22 | CREPE pitch detection (PyTorch)      |
| essentia    | ≥2.1b6  | Melodia, spectral analysis           |
| aubio       | ≥0.4.9  | Real-time pitch (future)             |
| soundfile   | ≥0.12   | Audio I/O (WAV, FLAC)               |
| pydub       | ≥0.25   | MP3→WAV conversion, format handling  |

### 4.3 Machine Learning
| Library      | Version | Purpose                              |
|-------------|---------|--------------------------------------|
| torch       | ≥2.1    | Primary ML framework                 |
| torchvision | ≥0.16   | CNN architectures for spectrograms   |
| torchaudio  | ≥2.1    | Audio transforms, mel spectrograms   |
| scikit-learn| ≥1.3    | Evaluation metrics, baseline models  |
| numpy       | ≥1.26   | Numerical computing                  |

### 4.4 API & Web
| Library      | Version | Purpose                              |
|-------------|---------|--------------------------------------|
| fastapi     | ≥0.104  | Production REST API                  |
| uvicorn     | ≥0.24   | ASGI server                          |
| streamlit   | ≥1.28   | Rapid prototyping web UI             |
| python-multipart | ≥0.0.6 | File upload handling             |

### 4.5 Database & Storage
| Technology   | Purpose                                     |
|-------------|----------------------------------------------|
| PostgreSQL  | Production: raga DB, user data, analysis logs |
| SQLite      | Development/testing                           |
| SQLAlchemy  | ORM (version ≥2.0)                           |
| Alembic     | Database migrations                          |

### 4.6 Development Tools
| Tool         | Purpose                                     |
|-------------|----------------------------------------------|
| ruff        | Linting + formatting (replaces black+flake8) |
| pytest      | Testing framework                            |
| pytest-cov  | Coverage reporting                           |
| pre-commit  | Git hook management                          |
| mypy        | Static type checking                         |

### 4.7 Infrastructure (Production)
| Service      | Purpose                                     |
|-------------|----------------------------------------------|
| AWS Lambda / Google Cloud Functions | Serverless inference   |
| AWS S3 / GCS | Audio file storage                          |
| Docker      | Containerization                             |
| GitHub Actions | CI/CD                                     |

---

## 5. Data Requirements

### 5.1 Training Data (Phase 1 — MVP)
| Dataset              | Quantity     | Source                          |
|----------------------|--------------|---------------------------------|
| Vocal recordings     | 20+ hours    | In-house musicians (CRJ Studio) |
| Gamaka annotations   | 1000+ segments | Expert musicians               |
| Raga-labeled tracks  | 100+ tracks  | Public datasets + in-house      |

### 5.2 Configuration Data (Provided with code)
- Swara frequency mappings (JSON) — `configs/swarasthanas.json`
- Raga definitions (JSON) — `configs/ragas/*.json`
- Tuning presets — `configs/tuning.json`

### 5.3 Annotation Format
```json
{
  "file": "track_001.wav",
  "sample_rate": 44100,
  "reference_sa_hz": 261.63,
  "annotations": [
    {
      "start_ms": 1200,
      "end_ms": 1450,
      "swara": "Ga3",
      "gamaka": "Kampita",
      "confidence": 0.95
    }
  ]
}
```

---

## 6. API Design

### 6.1 Core Endpoints

```
POST /api/v1/analyze
  Input: audio file (WAV/MP3) + reference_sa_hz (optional)
  Output: pitch contour + swara sequence + detected gamakas

POST /api/v1/identify-raga
  Input: swara sequence (from /analyze or manual)
  Output: ranked raga candidates with confidence

POST /api/v1/transcribe
  Input: audio file + raga (optional, for disambiguation)
  Output: full notation in selected script(s)

POST /api/v1/synthesize  [Phase 3]
  Input: notation + instrument + tempo
  Output: synthesized audio file

GET /api/v1/ragas
  Output: searchable raga database

GET /api/v1/swarasthanas?script=kannada
  Output: swara reference table in requested script
```

---

## 7. Performance Targets

| Metric                        | Target (MVP)        |
|-------------------------------|---------------------|
| Pitch detection accuracy      | ±10 cents           |
| Swara identification accuracy | >90% on clean audio |
| Gamaka classification (top-3) | >80% accuracy       |
| Raga ID (72 Melakarta)        | >85% accuracy       |
| API response time (30s clip)  | <5 seconds          |
| Audio formats supported       | WAV, MP3, FLAC      |

---

## 8. Security & Privacy

- Audio files are processed and discarded unless user opts in to storage
- No PII collected in MVP (anonymous usage)
- API rate limiting: 60 requests/minute per IP
- HTTPS enforced in production
- Model weights are not user-accessible (served via API only)
