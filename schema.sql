-- HardForge Database Schema (Supabase/PostgreSQL)

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enum types
CREATE TYPE subscription_tier AS ENUM ('free', 'pro', 'team');
CREATE TYPE project_status AS ENUM ('draft', 'designing', 'complete', 'archived');
CREATE TYPE driver_type AS ENUM ('woofer', 'midrange', 'tweeter', 'full_range', 'subwoofer');
CREATE TYPE curve_source AS ENUM ('calculated', 'measured', 'user_upload');
CREATE TYPE artifact_type AS ENUM ('schematic_svg', 'kicad_project', 'gerber_zip', 'bom_csv', 'bom_json', 'netlist');

-- Users (extends Supabase auth.users)
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    name TEXT,
    subscription_tier subscription_tier NOT NULL DEFAULT 'free',
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    designs_this_month INTEGER NOT NULL DEFAULT 0,
    designs_month_reset TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Projects
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    status project_status NOT NULL DEFAULT 'draft',
    design_intent JSONB,      -- Parsed NLP output
    circuit_design JSONB,     -- Full circuit design with components
    feasibility_report JSONB, -- AI feasibility analysis
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_status ON projects(status);

-- Loudspeaker Driver Database (TS Parameters)
CREATE TABLE drivers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    manufacturer TEXT NOT NULL,
    model TEXT NOT NULL,
    driver_type driver_type NOT NULL,
    -- Thiele-Small Parameters
    re DOUBLE PRECISION NOT NULL,           -- DC resistance (Ohms)
    le DOUBLE PRECISION,                     -- Voice coil inductance (mH)
    fs DOUBLE PRECISION NOT NULL,           -- Resonance frequency (Hz)
    qms DOUBLE PRECISION NOT NULL,          -- Mechanical Q factor
    qes DOUBLE PRECISION NOT NULL,          -- Electrical Q factor
    qts DOUBLE PRECISION NOT NULL,          -- Total Q factor
    vas DOUBLE PRECISION,                    -- Equivalent compliance volume (liters)
    bl DOUBLE PRECISION,                     -- Force factor (T·m)
    mms DOUBLE PRECISION,                    -- Moving mass (grams)
    cms DOUBLE PRECISION,                    -- Compliance (mm/N)
    rms DOUBLE PRECISION,                    -- Mechanical resistance (kg/s)
    sd DOUBLE PRECISION,                     -- Effective piston area (cm²)
    xmax DOUBLE PRECISION,                   -- Maximum excursion (mm)
    nominal_impedance DOUBLE PRECISION NOT NULL DEFAULT 8, -- Nominal impedance (Ohms)
    power_rating DOUBLE PRECISION,           -- Power rating (Watts RMS)
    sensitivity DOUBLE PRECISION,            -- Sensitivity (dB SPL @ 1W/1m)
    -- Metadata
    source_url TEXT,
    is_system BOOLEAN NOT NULL DEFAULT FALSE, -- System-provided vs user-added
    added_by UUID REFERENCES profiles(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_drivers_manufacturer ON drivers(manufacturer);
CREATE INDEX idx_drivers_type ON drivers(driver_type);
CREATE INDEX idx_drivers_search ON drivers USING gin(to_tsvector('english', manufacturer || ' ' || model));

-- Impedance Curves
CREATE TABLE impedance_curves (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    driver_id UUID REFERENCES drivers(id) ON DELETE SET NULL,
    name TEXT,
    source curve_source NOT NULL,
    frequency DOUBLE PRECISION[] NOT NULL,   -- Hz
    magnitude DOUBLE PRECISION[] NOT NULL,   -- Ohms
    phase DOUBLE PRECISION[],                -- Degrees
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_impedance_curves_driver ON impedance_curves(driver_id);

-- Export Artifacts
CREATE TABLE export_artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    type artifact_type NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '30 days'
);

CREATE INDEX idx_artifacts_project ON export_artifacts(project_id);

-- Row Level Security
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE impedance_curves ENABLE ROW LEVEL SECURITY;
ALTER TABLE export_artifacts ENABLE ROW LEVEL SECURITY;

-- Users can only see their own profile
CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);

-- Users can only see their own projects
CREATE POLICY "Users can view own projects" ON projects
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create projects" ON projects
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own projects" ON projects
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own projects" ON projects
    FOR DELETE USING (auth.uid() = user_id);

-- Drivers are readable by all, writable by owner
CREATE POLICY "Drivers are publicly readable" ON drivers
    FOR SELECT USING (TRUE);

-- Impedance curves: system ones are public, user ones are private
CREATE POLICY "System curves are public" ON impedance_curves
    FOR SELECT USING (user_id IS NULL OR auth.uid() = user_id);
CREATE POLICY "Users can create curves" ON impedance_curves
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Artifacts are private to project owner
CREATE POLICY "Users can view own artifacts" ON export_artifacts
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM projects
            WHERE projects.id = export_artifacts.project_id
            AND projects.user_id = auth.uid()
        )
    );

-- Function to reset monthly design count
CREATE OR REPLACE FUNCTION reset_monthly_designs()
RETURNS void AS $$
BEGIN
    UPDATE profiles
    SET designs_this_month = 0,
        designs_month_reset = NOW()
    WHERE designs_month_reset IS NULL
       OR designs_month_reset < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;
