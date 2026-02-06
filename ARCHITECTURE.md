# HardForge — Architecture Document

## Overview

HardForge is an AI-powered hardware design assistant that takes natural language descriptions of analog/mixed-signal hardware projects and guides users from concept through feasibility analysis, component selection, circuit design, schematic generation, and PCB/Gerber file output.

## Stack

### Frontend
- **Next.js 14** (App Router) — React framework with server-side rendering
- **TypeScript** — Type safety throughout
- **Tailwind CSS + shadcn/ui** — Styling and component library
- **Recharts** — Interactive impedance/frequency response plots with log axes
- **Deployed on:** Vercel

### Backend
- **FastAPI** (Python 3.11+) — REST API serving all EDA computation
- **Pydantic v2** — Request/response validation and serialization
- **Deployed on:** Railway or Fly.io

### Compute Engine (`/engine`)
- **NumPy/SciPy** — Impedance modeling, filter math, TS parameter calculations
- **SKiDL** — Programmatic circuit description → KiCad netlists
- **PySpice** (optional) — SPICE circuit simulation
- All math is pure Python+NumPy — no external EDA tools required at runtime

### AI Layer
- **Claude API** (`claude-sonnet-4-5-20250929`) — Natural language understanding
  - Intent parsing: NL description → structured DesignIntent
  - Feasibility analysis: physics-aware reasoning about design viability
  - Component selection: knowledge-based recommendations
  - Topology recommendation: circuit architecture suggestions

### Data & Auth
- **Supabase** — PostgreSQL database, auth, file storage
- **Stripe** — Subscription billing (Free / Pro $14.99 / Team $49.99)

## Data Models

### User
```
id: UUID (PK)
email: string
name: string
subscription_tier: enum('free', 'pro', 'team')
stripe_customer_id: string?
designs_this_month: int
created_at: timestamp
```

### Project
```
id: UUID (PK)
user_id: UUID (FK → User)
name: string
description: string
status: enum('draft', 'designing', 'complete', 'archived')
design_intent: JSON (DesignIntent)
circuit_design: JSON (CircuitDesign)
created_at: timestamp
updated_at: timestamp
```

### DesignIntent (JSON structure)
```
project_type: enum('impedance_correction', 'passive_crossover', 'filter', 'amplifier', 'power_supply', 'custom')
target_specs: {
  driver?: { manufacturer, model, ts_params }
  impedance_target?: number (ohms)
  crossover_freq?: number (Hz)
  crossover_type?: string
  filter_type?: string
  filter_freq?: number
  ...
}
constraints: {
  budget?: number
  form_factor?: string ('smd', 'through_hole', 'mixed')
  max_power?: number (watts)
}
components_mentioned: string[]
ambiguities: string[]
```

### CircuitDesign (JSON structure)
```
topology: string
components: [{
  ref: string ('R1', 'C1', 'L1')
  type: enum('resistor', 'capacitor', 'inductor', 'driver', 'opamp', ...)
  value: number
  unit: string
  footprint: string
  power_rating?: number
  tolerance?: string
  e_series_snapped?: { target: number, actual: number, error_pct: number }
}]
connections: [{ from: string, to: string, net: string }]
subcircuits: [{ name: string, type: string, components: string[] }]
warnings: string[]
simulation_results?: JSON
```

### ImpedanceCurve
```
id: UUID (PK)
user_id: UUID? (FK → User, null for system curves)
driver_id: UUID? (FK → Driver)
source: enum('calculated', 'measured', 'user_upload')
frequency: float[] (Hz)
magnitude: float[] (Ohms)
phase: float[] (degrees)
created_at: timestamp
```

### Driver (TS Parameters)
```
id: UUID (PK)
manufacturer: string
model: string
driver_type: enum('woofer', 'midrange', 'tweeter', 'full_range', 'subwoofer')
re: float (DC resistance, Ohms)
le: float (voice coil inductance, mH)
fs: float (resonance frequency, Hz)
qms: float (mechanical Q)
qes: float (electrical Q)
qts: float (total Q)
vas: float (equivalent compliance volume, liters)
bl: float (force factor, T·m)
mms: float (moving mass, grams)
cms: float (compliance, mm/N)
rms: float (mechanical resistance, kg/s)
sd: float (effective piston area, cm²)
xmax: float (max excursion, mm)
nominal_impedance: float (ohms)
power_rating: float (watts RMS)
sensitivity: float (dB SPL @ 1W/1m)
source_url: string?
```

### ExportArtifact
```
id: UUID (PK)
project_id: UUID (FK → Project)
type: enum('schematic_svg', 'kicad_project', 'gerber_zip', 'bom_csv', 'bom_json', 'netlist')
file_path: string
file_size: int
created_at: timestamp
expires_at: timestamp?
```

## API Routes

### AI Pipeline
| Method | Path | Description | Auth | Tier |
|--------|------|-------------|------|------|
| POST | /api/parse-intent | NL description → DesignIntent | Yes | All |
| POST | /api/analyze-feasibility | DesignIntent → FeasibilityReport | Yes | All |
| POST | /api/design-circuit | DesignIntent + topology → CircuitDesign | Yes | All |

### Computation
| Method | Path | Description | Auth | Tier |
|--------|------|-------------|------|------|
| POST | /api/calculate-components | TS params/curve → component values | Yes | All |
| POST | /api/calculate-impedance | TS params → impedance curve | No | All |
| POST | /api/simulate | CircuitDesign → simulation results | Yes | Pro+ |

### Export
| Method | Path | Description | Auth | Tier |
|--------|------|-------------|------|------|
| POST | /api/generate-schematic | CircuitDesign → SVG + .kicad_sch | Yes | All* |
| POST | /api/generate-gerber | CircuitDesign → Gerber ZIP | Yes | Pro+ |
| POST | /api/generate-bom | CircuitDesign → BOM | Yes | All |

*Free tier: SVG only. Pro+: full KiCad project.

### Library
| Method | Path | Description | Auth | Tier |
|--------|------|-------------|------|------|
| GET | /api/library/drivers | Search TS parameter database | No | All |
| GET | /api/library/drivers/:id | Get driver details + impedance | No | All |
| GET | /api/library/impedance-curves | Browse impedance curves | No | All |
| POST | /api/library/impedance-curves | Upload measured impedance CSV | Yes | All |
| GET | /api/library/topologies | List circuit topologies | No | All |

### Auth & Billing
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/auth/signup | Create account |
| POST | /api/auth/login | Login |
| POST | /api/checkout | Create Stripe checkout session |
| POST | /api/webhook/stripe | Stripe webhook handler |

## File Structure

```
hardforge/
├── frontend/               # Next.js 14 app
│   ├── src/
│   │   ├── app/            # App router pages
│   │   │   ├── page.tsx              # Landing page
│   │   │   ├── layout.tsx            # Root layout
│   │   │   ├── design/[id]/page.tsx  # Design workspace
│   │   │   ├── tools/impedance/page.tsx  # Impedance tool
│   │   │   ├── library/
│   │   │   │   ├── drivers/page.tsx
│   │   │   │   └── components/page.tsx
│   │   │   └── dashboard/page.tsx
│   │   ├── components/     # React components
│   │   │   ├── ui/         # shadcn/ui components
│   │   │   ├── workspace/  # Design workspace components
│   │   │   ├── plots/      # Impedance/frequency plots
│   │   │   └── layout/     # Shell, nav, sidebar
│   │   ├── lib/            # Utilities, API client, hooks
│   │   └── types/          # TypeScript type definitions
│   ├── public/
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── backend/                # FastAPI Python service
│   ├── main.py             # App entry point
│   ├── routes/
│   │   ├── intent.py       # /api/parse-intent
│   │   ├── feasibility.py  # /api/analyze-feasibility
│   │   ├── design.py       # /api/design-circuit
│   │   ├── export.py       # /api/generate-*
│   │   ├── library.py      # /api/library/*
│   │   └── auth.py         # Auth & billing routes
│   ├── ai/
│   │   └── prompts.py      # Claude prompt engineering
│   ├── middleware/
│   │   ├── auth.py         # Auth verification
│   │   ├── rate_limit.py   # Rate limiting
│   │   └── tier_check.py   # Subscription tier enforcement
│   └── requirements.txt
│
├── engine/                 # Core computation engine
│   ├── __init__.py
│   ├── impedance.py        # Impedance modeling from TS params
│   ├── correction.py       # Correction network design
│   ├── topology.py         # Circuit topology definitions
│   ├── skidl_gen.py        # SKiDL circuit generation
│   ├── kicad_export.py     # KiCad file generation
│   ├── simulation.py       # Circuit simulation
│   ├── bom.py              # Bill of materials
│   ├── ts_database.py      # TS parameter database
│   ├── components.py       # E-series values, standard parts
│   └── tests/
│       ├── test_impedance.py
│       ├── test_correction.py
│       ├── test_topology.py
│       └── test_components.py
│
├── data/
│   ├── drivers/            # TS parameter JSON files
│   │   └── seed_drivers.json
│   ├── impedance_curves/   # Example measured impedance CSVs
│   └── examples/           # Pre-built example projects
│
├── shared/                 # Shared types (TypeScript)
│   └── types.ts
│
├── ARCHITECTURE.md         # This file
├── CLAUDE.md               # Architectural decision log
├── SKEPTIC_REPORT.md       # Skeptic agent findings
├── docker-compose.yml
├── .env.example
└── README.md
```

## Key Design Decisions

1. **Separate Python backend**: EDA libraries (SKiDL, NumPy, SciPy) are Python-only. No viable JS alternatives exist with comparable accuracy.

2. **JSON-based circuit representation**: CircuitDesign is stored as JSON rather than in normalized SQL tables. This allows flexible schema evolution and easy serialization. The engine operates on these JSON structures directly.

3. **Stateless computation**: Each API call contains all necessary data. The backend doesn't hold circuit state in memory between requests. This simplifies scaling and eliminates session stickiness requirements.

4. **SVG for schematic preview**: Browser-native, scalable, interactive. No need for canvas libraries. Components can have hover/click handlers for editing.

5. **Claude for reasoning, engine for math**: Claude handles natural language understanding, feasibility reasoning, and topology recommendation. All numerical calculations happen in the deterministic Python engine. Claude never calculates component values directly.

6. **Free impedance calculator**: The `/tools/impedance` endpoint is the viral entry point. It works without auth, drives SEO traffic, and demonstrates value before asking for signup.
