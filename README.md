# HardForge

AI-powered hardware design assistant that takes natural language descriptions of analog/mixed-signal hardware projects and produces schematics, KiCad files, and Gerber outputs.

## Quick Start

### Prerequisites
- Node.js 20+
- Python 3.9+
- Anthropic API key (for AI features)

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

### Backend (FastAPI)

```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Run the backend
uvicorn backend.main:app --reload --port 8000
```

### Docker (Both Services)

```bash
cp .env.example .env
# Edit .env with your API keys
docker-compose up
```

## Architecture

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, Recharts
- **Backend**: FastAPI (Python), Claude AI integration
- **Engine**: Pure Python computation (NumPy/SciPy) for impedance modeling, correction networks, crossover design
- **Export**: SVG schematics, KiCad project files, SKiDL code generation

See [ARCHITECTURE.md](ARCHITECTURE.md) for full details.

## Features

- **Natural Language Input**: Describe your hardware project, get a structured design
- **Impedance Modeling**: Calculate loudspeaker impedance from Thiele-Small parameters
- **Correction Networks**: Zobel networks, resonance notch filters, full admittance shapers
- **Passive Crossovers**: 1st–4th order Butterworth, Linkwitz-Riley, Bessel
- **Schematic Export**: SVG preview, KiCad project files, SKiDL Python code
- **Driver Library**: 50+ loudspeaker drivers with TS parameters
- **Interactive Plots**: Log-frequency impedance curves with dual Y-axis

## Project Structure

```
hardforge/
├── frontend/          # Next.js 14 app
├── backend/           # FastAPI Python service
│   ├── routes/        # API endpoints
│   ├── ai/            # Claude prompt engineering
│   └── middleware/     # Auth, rate limiting
├── engine/            # Core computation (pure Python)
│   ├── impedance.py   # TS parameter → impedance curves
│   ├── correction.py  # Zobel + notch network design
│   ├── topology.py    # Circuit topology definitions
│   ├── kicad_export.py # SVG + KiCad file generation
│   ├── skidl_gen.py   # SKiDL code generation
│   ├── bom.py         # Bill of materials
│   ├── ts_database.py # 50+ driver TS parameter database
│   └── tests/         # Unit tests (77/78 passing)
└── data/              # Seed data, example files
```

## Running Tests

```bash
# Engine unit tests
python -m pytest engine/tests/ -v

# Frontend build check
cd frontend && npm run build
```

## Pricing

- **Free**: 3 designs/month, impedance calculator, SVG export
- **Pro ($14.99/mo)**: Unlimited designs, KiCad export, Gerber generation, SPICE simulation
- **Team ($49.99/mo)**: Shared library, version history, collaboration
