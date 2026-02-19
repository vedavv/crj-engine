# CRJ Engine - Project Guide

## What is this?
CRJ Engine is the core AI/ML audio processing engine for CRJ Studio (Create / Refine / Jubilate).
It converts audio frequencies into musical notation across Western and Indian classical systems,
with specialized support for Carnatic, Hindustani, and Sama Veda traditions.

## Project Structure
```
crj-engine/
├── src/crj_engine/       # Main Python package
│   ├── pitch/            # Pitch detection (CREPE, librosa, Essentia)
│   ├── swara/            # Swara mapping, multilingual transliteration
│   ├── raga/             # Raga identification, enharmonic disambiguation
│   ├── synthesis/        # Audio synthesis, instrument-specific rendering
│   └── api/              # REST API endpoints (Flask/FastAPI)
├── tests/                # Test suite (pytest)
├── data/
│   ├── peer-test/audio/  # Test audio samples
│   ├── training/         # Training datasets (not committed)
│   └── models/           # Trained model weights (not committed)
├── configs/              # Swara mappings, raga definitions, tuning configs
├── docs/                 # Technical documentation
├── scripts/              # Utility scripts (training, data prep, benchmarks)
└── web/                  # Streamlit/Flask web prototype
```

## Tech Stack
- **Language**: Python 3.11+
- **Audio**: librosa, CREPE, Essentia, Aubio, soundfile
- **ML**: PyTorch (primary), TensorFlow (CREPE compatibility)
- **API**: FastAPI (production), Streamlit (prototyping)
- **Database**: PostgreSQL (production), SQLite (dev)
- **Testing**: pytest, pytest-cov
- **Formatting**: ruff (linting + formatting)

## Key Conventions
- All frequency calculations use A4 = 440 Hz as Western reference
- Indian swara calculations are relative to a configurable Shadja (Sa) frequency
- Cent-based comparison: `cents = 1200 * log2(freq / reference_sa)`
- Multilingual output: Devanagari, Kannada, Tamil, Telugu, Scientific (IAST)
- Audio input: WAV preferred, MP3 accepted (converted internally to WAV)

## Development Commands
```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/
ruff format src/ tests/

# Run web prototype
streamlit run web/app.py

# Run API server
uvicorn crj_engine.api.main:app --reload
```

## Important Notes
- Large audio files and model weights go in data/ but are .gitignored
- Training data requires expert musician annotation — see docs/TECH_SPEC.md
- Gamaka types: Kampita, Jaru, Sphuritham, Meend (and more in later phases)
- MVP scope: Carnatic vocal input, top 3 gamakas, 12 swarasthanas
