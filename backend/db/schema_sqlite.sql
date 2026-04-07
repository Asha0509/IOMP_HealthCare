-- SQLite-compatible schema for AI Healthcare Triage System

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    age INTEGER,
    gender TEXT,
    comorbidities TEXT, -- comma-separated
    language_preference TEXT DEFAULT 'en',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- Triage sessions
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    session_token TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'active',
    chief_complaint TEXT,
    patient_age INTEGER,
    patient_gender TEXT,
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    question_index INTEGER DEFAULT 0,
    total_questions INTEGER DEFAULT 0
);

-- Extracted symptoms per session
CREATE TABLE IF NOT EXISTS session_symptoms (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    symptom_key TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS triage_results (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    triage_label TEXT,
    confidence REAL,
    probabilities TEXT, -- JSON string
    red_flag_triggered BOOLEAN,
    red_flag_reason TEXT,
    explanation_text TEXT,
    recommended_action TEXT,
    diseases_considered TEXT, -- JSON string
    shap_values TEXT, -- JSON string
    remedies TEXT, -- JSON string
    nutrition_tips TEXT, -- JSON string
    medications TEXT, -- JSON string
    crisis_response BOOLEAN,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Audit logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    event_type TEXT,
    event_data TEXT, -- JSON string
    ip_hash TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
