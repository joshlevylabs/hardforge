# HardForge — Architectural Decision Log

All agents append their decisions here. This is the single source of truth for "why was this built this way?"

---

## Architect — 2026-02-06

### Decision: Separate Python backend from Next.js frontend
**Reasoning:** EDA libraries (SKiDL, NumPy, SciPy, pcbnew) are Python-only. No viable JavaScript alternatives exist with comparable accuracy for circuit simulation and impedance modeling. A FastAPI microservice provides clean separation and allows independent scaling of compute-heavy operations.
**Alternatives rejected:**
- Pyodide (Python in browser) — too slow for NumPy operations, SKiDL has native dependencies
- Node.js FFI to Python — fragile, hard to debug
- All-in-one Next.js with API routes calling Python scripts — messy process management

### Decision: JSON-based circuit representation (not normalized SQL)
**Reasoning:** Circuit designs have highly variable structure (a Zobel network has 2 components, a 4th-order crossover has 12+). JSON allows flexible schema evolution, easy serialization between frontend/backend/engine, and direct use as engine input. Querying individual component values across designs is not a use case.
**Alternatives rejected:**
- Fully normalized SQL (components table, connections table) — over-engineering for the use case, would require complex JOINs for every design load

### Decision: Claude for reasoning, engine for math
**Reasoning:** LLMs hallucinate numbers. All component value calculations MUST happen in the deterministic Python engine. Claude's role is limited to: (1) parsing natural language intent, (2) reasoning about feasibility, (3) recommending topologies, (4) explaining designs to users. Claude never outputs component values directly.
**Alternatives rejected:**
- Claude calculates everything — would produce incorrect component values
- No AI at all — loses the key differentiator (natural language → hardware)

### Decision: Stateless backend computation
**Reasoning:** Each API call contains all necessary data (TS params, design choices, etc.). No server-side session state. This simplifies horizontal scaling, eliminates sticky sessions, and makes the system more resilient to restarts.

### Decision: Free impedance calculator as viral entry point
**Reasoning:** `/tools/impedance` works without authentication. It targets high-intent SEO keywords ("impedance correction calculator", "Zobel network calculator"). Users see value immediately, then are incentivized to sign up for full design + export features.

### Decision: Dark mode default with electric blue accent
**Reasoning:** Engineers spend long hours in dark environments. Dark mode reduces eye strain. Electric blue (#3B82F6) provides high contrast for interactive elements and data visualization without being garish.

---

## Frontend Engineer — 2026-02-06

### Decision: Tailwind v4 CSS-based theme configuration (no tailwind.config.ts)
**Reasoning:** create-next-app@latest ships Tailwind v4 with `@tailwindcss/postcss`. Tailwind v4 uses CSS `@theme` directives for configuration instead of the old JavaScript config file. All custom colors (accent, surface variants, text hierarchy), fonts (Inter, JetBrains Mono), and theme tokens are defined directly in `globals.css` using `@theme inline {}`.
**Alternatives rejected:**
- Downgrading to Tailwind v3 for `tailwind.config.ts` — unnecessary friction, v4 is the current default
- Creating a tailwind.config.ts alongside v4 — incompatible, v4 doesn't read JS config files

### Decision: Hand-built shadcn-style components (no shadcn CLI)
**Reasoning:** shadcn/ui CLI has compatibility issues with Tailwind v4 and latest Radix versions. Building components manually with the same patterns (forwardRef, cn() class merging, cva for variants) provides full control and guaranteed compatibility. Components use the project's custom theme tokens directly.
**Alternatives rejected:**
- shadcn/ui CLI init — generates Tailwind v3 config that conflicts with v4

### Decision: Recharts with log-scale XAxis for impedance plots
**Reasoning:** Impedance curves are always plotted on a logarithmic frequency axis (20Hz-20kHz). Recharts supports `scale="log"` on XAxis natively. Custom tick values at decade boundaries (20, 50, 100, 200, 500, 1k, 2k, 5k, 10k, 20k) match standard audio engineering conventions. Dual Y-axis (magnitude left, phase right) follows industry standard presentation.
**Alternatives rejected:**
- D3.js — lower-level, more code for the same result, harder to maintain
- Chart.js — weaker log-scale support, less React-native

### Decision: Client-side impedance calculation for mock/demo mode
**Reasoning:** The frontend includes a simplified impedance model in `mock-data.ts` using TS parameter equations. This allows the impedance tool and workspace to function fully without a backend connection during development and demo. The model is physically reasonable (resonance peak at fs, rising impedance from Le) but intentionally simplified — production calculations happen in the Python engine.
**Alternatives rejected:**
- Backend-dependent only — blocks frontend development, makes demos fragile

### Decision: Three-panel workspace layout (navigator / tabs / properties)
**Reasoning:** Modeled after Figma/KiCad workflow. Left panel shows project state and pipeline progress. Center panel provides tabbed views (chat, schematic, impedance, simulation, PCB). Right panel shows context-sensitive properties. This maximizes information density for engineering workflows without overwhelming new users. The layout uses `h-[calc(100vh-3.5rem)]` to fill viewport below navbar.
**Alternatives rejected:**
- Single-panel with modal dialogs — too much context switching for iterative design work
- Floating panels — harder to maintain consistent layout, accessibility concerns

### Decision: Google Fonts via `<link>` instead of next/font
**Reasoning:** Inter and JetBrains Mono from Google Fonts via `<link>` tags. next/font's local font optimization is ideal for production but adds complexity during rapid prototyping. The preconnect hints minimize FOIT. Can be migrated to next/font for production optimization.
**Alternatives rejected:**
- next/font/google — adds build-time complexity, the default Geist fonts don't match the engineering tool aesthetic

---

## Compute Engine — 2026-02-06

### Decision: Q-factor fallback path for impedance modeling
**Reasoning:** Many driver datasheets omit BL (force factor), Mms (moving mass), Cms (compliance), and Rms (mechanical resistance). The Q-factor equivalents (Res = Re·Qms/Qes, Lces = Qes·Re/(2πfs), Cmes = 1/(2πfs·Qes·Re)) are algebraically equivalent and derivable from parameters that every datasheet includes. Both paths are implemented; the BL-path is used when all mechanical parameters are available, otherwise Q-factor path is used.
**Alternatives rejected:**
- Require all parameters — would exclude most drivers from the database
- Estimate missing parameters — introduces uncontrolled error

### Decision: Logarithmic interpolation for impedance data
**Reasoning:** Impedance measurements and calculations are plotted on log-frequency axes. Interpolating in log-log space (log frequency, log magnitude) produces visually smooth curves that match the physical behavior. Linear interpolation in log-log space corresponds to power-law interpolation in linear space, which is the correct behavior for impedance (Z ∝ f for inductors, Z ∝ 1/f for capacitors).
**Alternatives rejected:**
- Linear interpolation — produces visible artifacts on log-scale plots
- Spline interpolation — can introduce oscillations, harder to guarantee monotonicity

### Decision: Normalized prototype filter coefficients for crossover design
**Reasoning:** Rather than hard-coding denormalized component values for each combination of order/alignment/impedance/frequency, we store normalized Q factors per filter section (Butterworth, Linkwitz-Riley, Bessel). Denormalization is: L = L_norm·R/ωc, C = C_norm/(ωc·R) where L_norm = 1/Q, C_norm = Q. This handles arbitrary impedance and frequency with a single set of coefficients. Standard verified values: 2nd-order Butterworth Q = 1/√2, LR4 uses two Q = 1/√2 sections, Bessel Q values from Zverev tables.
**Alternatives rejected:**
- Lookup tables of denormalized values — doesn't scale, error-prone for non-standard impedances
- Transfer function polynomial approach — correct but harder to map to physical component values

### Decision: Analytical simulation instead of SPICE
**Reasoning:** For passive networks (RLC + resistive load), the transfer function is a simple impedance divider: H(f) = Z_load / (Z_series + Z_load). This is exact for the circuit topologies HardForge generates (crossovers, Zobel, notch filters). No external SPICE engine is needed, eliminating a deployment dependency. PySpice remains optional for users who want to verify with a full SPICE simulation.
**Alternatives rejected:**
- Require PySpice/ngspice — adds system dependency, complicates Docker deployment
- Browser-based SPICE.js — too slow for 500+ frequency points

### Decision: SKiDL code generation as string output (no SKiDL runtime dependency)
**Reasoning:** SKiDL depends on KiCad being installed, which is heavy (500MB+). The engine generates SKiDL Python source code as a string that users can run independently. The netlist generation function produces KiCad-format netlists directly using string manipulation, with no KiCad dependency at runtime. This keeps the Docker image small and the engine portable.
**Alternatives rejected:**
- Import SKiDL at runtime — requires KiCad installation on the server
- Custom netlist format — not compatible with any EDA tool

### Decision: SVG schematic generation with EDA-standard symbols
**Reasoning:** SVG is browser-native, scalable, and can include interactive elements (hover, click). The engine draws proper EDA symbols: zigzag resistors, parallel-plate capacitors, coil inductors. Dark background (#0f172a) with light strokes (#e2e8f0) and electric blue accents (#3B82F6) match the frontend theme. Components are labeled with engineering notation values.
**Alternatives rejected:**
- Canvas rendering — not scalable, no DOM interaction, not server-renderable
- PDF export — harder to embed in web UI

### Decision: 51 seed drivers from 20 manufacturers
**Reasoning:** The TS parameter database is seeded with real drivers that audio engineers commonly use (Dayton Audio RS series, SB Acoustics, Seas, Peerless/Tymphany, Scan-Speak, etc.). All parameters sourced from manufacturer datasheets. This provides immediate utility without requiring users to manually enter parameters. The database uses a class with deterministic UUID5 IDs (based on manufacturer:model) for stable references.
**Alternatives rejected:**
- Empty database requiring user input — poor first-run experience
- Scraping web databases — licensing/legal issues, data quality concerns

### Decision: E-series snapping uses geometric (log-scale) distance
**Reasoning:** E-series values are geometrically spaced (each value is approximately the previous × a constant ratio). When snapping to the nearest standard value, we compare log10(value) distances rather than linear distances. This correctly handles the fact that 4.7kΩ and 5.1kΩ are "equally spaced" in the E24 sense, even though their linear difference (400Ω) is much larger than between 1.0Ω and 1.1Ω (0.1Ω).
**Alternatives rejected:**
- Linear distance — biases toward larger values in each decade
- Percentage distance — equivalent to log distance, but less numerically stable

---

## Integrator — 2026-02-06

### Decision: Backend API functions matched to engine's actual return types
**Reasoning:** The engine functions return different types than initially assumed — `snap_to_e_series` returns `(value, error_pct)` tuples, `zobel_network` and `notch_filter` return dicts. The backend routes were updated to match the engine's actual API. Function names aligned: `engineering_notation` (not `format_engineering`), `full_correction` (not `full_correction_network`), `list_topologies` (not `get_all_topologies`).

### Decision: SVG XSS prevention via html.escape
**Reasoning:** Component reference designators and values are embedded in SVG `<text>` elements. Since these values could theoretically originate from user input (via custom component names), all text rendered into SVG is escaped using `html.escape()` to prevent XSS attacks when SVG is rendered in the browser.

### Decision: All 78 engine unit tests passing
**Reasoning:** The test suite validates all critical physics: impedance peak at fs, Zobel units, notch resonant frequency, corrected impedance flatness, E-series snapping, CSV parsing, and interpolation. Test coverage ensures the math is correct.

---

## Skeptic Review — 2026-02-06

### Risk Prioritization: Critical items before launch

**Priority 1 — Frontend notch filter formula is inverted (F-1)**
`mock-data.ts:200` uses `re * (qes / qms)` instead of `re * (qms / qes)`. This produces a resistor value ~110x too small. Also, the impedance peak formula on line 180 uses `re * (1 + qms * qes)` instead of `re * (1 + qms / qes)`, producing a peak ~3.5x too low. These are the most visible bugs — the free impedance tool shows wrong numbers.

**Priority 2 — Authentication is fully mocked (S-8/B-4)**
`tier_check.py` functions are no-ops. All API routes including AI-powered ones are open to the internet. Combined with bypassable IP-based rate limiting, this exposes the Anthropic API key to unbounded cost accumulation. Must implement auth before deploying with real API keys.

**Priority 3 — Prompt injection surface (S-1)**
User descriptions are concatenated directly into Claude messages without delimiters. While Claude has native guardrails, the system prompt schema could be exfiltrated. Wrap user input in `<user_input>` tags and add defensive instructions.

**Decision: Engine formulas are verified correct; frontend mock formulas need fixes**
The Python engine's impedance, correction, crossover, and E-series code all match textbook references (Beranek, Small, Dickason, Zverev). The frontend TypeScript mock calculations in `mock-data.ts` have two formula errors (inverted R_notch, wrong peak impedance) and use a non-physical impedance model. The backend correctly uses the engine for all production calculations — the frontend mock is only used in demo/offline mode.

**Decision: SVG XSS prevention is adequate**
`kicad_export.py` uses `html.escape()` on all user-controlled text before embedding in SVG. No injection vectors found.

**Decision: CSV upload needs streaming size check**
Currently reads full file into memory before checking size limit. Should check Content-Length or use chunked reading to prevent memory exhaustion from oversized uploads.

---

## Skeptic Remediation — 2026-02-06

### Fixes applied to address Skeptic findings:

- **F-1, F-2, F-3 (Frontend formulas):** Rewrote `generateImpedanceCurve()` to use the standard lumped-parameter model (Z = Re + jωLe + Zmot, Zmot from parallel RLC). Fixed R_notch from `re * (qes/qms)` to `re * (qms/qes)`. Rewrote `generateCorrectedCurve()` to use proper complex parallel impedance (Y_total = Y_driver + Y_zobel + Y_notch) instead of fake blend.
- **F-4 (Butterworth/Bessel Q):** Removed unused trailing Q values from 3rd-order arrays.
- **F-5 (Footprints):** `design.py` now calls `_select_footprint()` from `skidl_gen.py` for power-aware footprint selection.
- **S-1 (Prompt injection):** User input wrapped in `<user_input>` delimiters with explicit ignore-instructions rule in system prompts.
- **S-3 (CSV memory):** Chunked reading (8KB) with early rejection before full buffer.
- **S-7 (Rate limiter):** Added `_cleanup_stale_keys()` that prunes keys with no recent activity every 5 minutes.
- **U-2 (Upload CSV):** Button disabled with "Coming soon" label.
- **U-7 (Error messages):** All backend `HTTPException` details now use generic messages; internal exceptions no longer exposed.
- **S-8/B-4, S-6, B-1, B-3:** Deferred — require Supabase integration for auth, storage, and billing.
