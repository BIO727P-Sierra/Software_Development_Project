-- ============================================================
-- Directed Evolution Portal — Database Schema
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS experiments (
    experiment_id       SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL,
    experiment_name     VARCHAR(255) NOT NULL,
    uniprot_id          VARCHAR(20) NOT NULL,
    wt_protein_sequence TEXT NOT NULL,
    wt_dna_sequence     TEXT NOT NULL DEFAULT '',
    uniprot_features    JSONB,
    plasmid_validated   BOOLEAN DEFAULT FALSE,
    validation_note     TEXT,
    metadata            JSONB,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_experiment_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS variants (
    variant_id              SERIAL PRIMARY KEY,
    experiment_id           INTEGER NOT NULL,
    plasmid_variant_index   INTEGER,
    parent_variant_id       INTEGER,
    generation              INTEGER NOT NULL,
    assembled_dna_sequence  TEXT NOT NULL,

    -- Step 1: ORF identification
    step1_status        TEXT,
    step1_error         TEXT,
    orf_start           INTEGER,
    orf_end             INTEGER,
    orf_strand          CHAR(1),
    orf_frame           INTEGER,
    orf_score           REAL,
    orf_coverage        REAL,
    orf_final           REAL,
    orf_protein_len     INTEGER,
    orf_cds_dna         TEXT,
    orf_protein_sequence TEXT,

    protein_sequence    TEXT NOT NULL DEFAULT '', 
    -- This is different to wt_protein_sequence, returned after orf analysis to lead into mutations
    activity_score      REAL,
    mutation_total      INTEGER,
    qc_passed           BOOLEAN DEFAULT TRUE,
    -- qc_passed could possibly be removed in future if need be 
    -- qc_reason TEXT, removed as only valid data will be stored
    metadata            JSONB,

    CONSTRAINT fk_variant_experiment
        FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id) ON DELETE CASCADE
    -- deleted the following  constraint to avoid errors with a -1 parent plasmid: 
    -- CONSTRAINT fk_parent_variant FOREIGN KEY (parent_variant_id) REFERENCES variants(variant_id)
);

CREATE TABLE IF NOT EXISTS measurements (
    measurement_id  SERIAL PRIMARY KEY,
    variant_id      INTEGER NOT NULL,
    dna_yield       FLOAT,
    protein_yield   FLOAT,
    is_control      BOOLEAN DEFAULT FALSE,

    CONSTRAINT fk_measurement_variant
        FOREIGN KEY (variant_id) REFERENCES variants(variant_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS mutations (
    mutation_id     SERIAL PRIMARY KEY,
    variant_id      INTEGER NOT NULL,
    position        INTEGER NOT NULL,
    wt_residue      CHAR(1),
    mutant_residue  CHAR(1),
    mutation_type   VARCHAR(20),

    CONSTRAINT fk_variant_mutation
        FOREIGN KEY (variant_id) REFERENCES variants(variant_id) ON DELETE CASCADE
);
