CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    -- Primary key is the column in a table that uniquely identifies each row.
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- Useful for any debugging and trace any uploads that went wrong, not necessary for project.
);

CREATE TABLE IF NOT EXISTS experiments (
    experiment_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    experiment_name VARCHAR(255) NOT NULL,
    uniprot_id VARCHAR(20) NOT NULL,
    -- UniProt accession number.
    wt_protein_sequence TEXT NOT NULL,
    -- Wild-type protein amino acid sequence inserted by user.
    wt_dna_sequence TEXT NOT NULL,
    -- Wild-type plasmid DNA sequence, inserted by user.
    uniprot_features JSONB,
    plasmid_validated BOOLEAN DEFAULT FALSE,
    validation_note TEXT,
    metadata JSONB,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_experiment_user FOREIGN KEY (user_id)
    -- Enforces the foreign key is user_id which refers to the primary key id of the users table.
    REFERENCES users(id) ON DELETE CASCADE
    -- If a user is deleted then experiments will be deleted too to avoid orphan experiments.
);

CREATE TABLE IF NOT EXISTS variants (
    variant_id SERIAL PRIMARY KEY,
    experiment_id INTEGER NOT NULL,
    plasmid_variant_index INTEGER,
    parent_variant_id INTEGER,
    -- Not sure if this is needed as this tracks the previous generation variant
    generation INTEGER NOT NULL,
    assembled_dna_sequence TEXT NOT NULL,
    -- Represents the plasmid variants
    protein_sequence TEXT NOT NULL,
    activity_score REAL,
    -- Calculated after parsing/QC
    mutation_total INTEGER,
    qc_passed BOOLEAN DEFAULT TRUE,
    qc_reason TEXT,
    -- Can be removed if not needed
    metadata JSONB,

    CONSTRAINT fk_variant_experiment FOREIGN KEY (experiment_id)
    REFERENCES experiments(experiment_id) ON DELETE CASCADE
    -- Ensures FK is taken from the experiments table

    CONSTRAINT fk_parent_variant FOREIGN KEY (parent_variant_id)
    REFERENCES variants(variant_id)
);
 
CREATE TABLE IF NOT EXISTS measurements (
    -- Table to store baseline dna and protein concentrations from wt controls for activity scores.
    measurement_id SERIAL PRIMARY KEY,
    variant_id INTEGER NOT NULL,
    dna_yield FLOAT,
    -- e.g. DNA_Quantification_fg
    protein_yield FLOAT,
    -- e.g. Protein_Quantification_fg
    is_control BOOLEAN DEFAULT FALSE,
    -- Will be TRUE if it is a control WT measurement

    CONSTRAINT fk_measurement_variant FOREIGN KEY (variant_id)
    REFERENCES variants(variant_id) ON DELETE CASCADE
 );

CREATE TABLE IF NOT EXISTS mutations (
    mutation_id SERIAL PRIMARY KEY,
    variant_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    wt_residue CHAR(1),
    mutant_residue CHAR(1),
    -- To identify the type of mutation
    mutation_type VARCHAR(20),

    CONSTRAINT fk_variant_mutation FOREIGN KEY (variant_id)
    REFERENCES variants(variant_id) ON DELETE CASCADE
);
