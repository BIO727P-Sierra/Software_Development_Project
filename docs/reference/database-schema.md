# Database Schema

The portal uses a PostgreSQL 16 database with five tables. The schema is applied automatically from `schema.sql` on first container startup.

---

## Entity relationship

```
users
  └── experiments (user_id → users.id)
        └── variants (experiment_id → experiments.experiment_id)
              ├── measurements (variant_id → variants.variant_id)
              └── mutations    (variant_id → variants.variant_id)
```

---

## users

Stores registered user accounts.

| Column | Type | Description |
|---|---|---|
| `id` | `SERIAL PK` | Auto-incrementing user ID |
| `email` | `VARCHAR(255) UNIQUE NOT NULL` | Login email address |
| `password_hash` | `VARCHAR(255) NOT NULL` | Werkzeug-hashed password |
| `created_at` | `TIMESTAMP` | Account creation time |

---

## experiments

One row per experiment, created at UniProt confirmation. Represents a single directed evolution campaign targeting one protein.

| Column | Type | Description |
|---|---|---|
| `experiment_id` | `SERIAL PK` | Auto-incrementing experiment ID |
| `user_id` | `INTEGER FK → users.id` | Owning user |
| `experiment_name` | `VARCHAR(255) NOT NULL` | Auto-generated: `"Experiment – {uniprot_id}"` |
| `uniprot_id` | `VARCHAR(20) NOT NULL` | UniProt accession ID (e.g. `P00533`) |
| `wt_protein_sequence` | `TEXT NOT NULL` | Wild-type protein sequence from UniProt |
| `wt_dna_sequence` | `TEXT NOT NULL DEFAULT ''` | Wild-type plasmid DNA; populated at plasmid upload |
| `uniprot_features` | `JSONB` | Array of `{feature_type, start_location, end_location}` from UniProt |
| `plasmid_validated` | `BOOLEAN DEFAULT FALSE` | Set to `TRUE` after successful FASTA validation |
| `validation_note` | `TEXT` | Optional note from validation step |
| `metadata` | `JSONB` | Reserved for future use |
| `created_at` | `TIMESTAMP` | Experiment creation time |

---

## variants

One row per plasmid variant in an experiment. DNA sequences and ORF analysis results live here.

### Identity and lineage

| Column | Type | Description |
|---|---|---|
| `variant_id` | `SERIAL PK` | Auto-incrementing variant ID |
| `experiment_id` | `INTEGER FK → experiments.experiment_id` | Parent experiment |
| `plasmid_variant_index` | `INTEGER` | Unique index from the uploaded data file |
| `parent_variant_id` | `INTEGER FK → variants.variant_id` | Parent variant (NULL until lineage resolution) |
| `generation` | `INTEGER NOT NULL` | Directed evolution generation number |

### Sequence data

| Column | Type | Description |
|---|---|---|
| `assembled_dna_sequence` | `TEXT NOT NULL` | Full assembled plasmid DNA sequence |
| `protein_sequence` | `TEXT NOT NULL DEFAULT ''` | Protein sequence if provided in upload file |

### Step 1 — ORF analysis results

These columns are all `NULL` until ORF analysis is run.

| Column | Type | Description |
|---|---|---|
| `step1_status` | `TEXT` | `'ok'` or `'error'` |
| `step1_error` | `TEXT` | Error message if `step1_status = 'error'` |
| `orf_start` | `INTEGER` | 0-based start coordinate of ORF in circular plasmid |
| `orf_end` | `INTEGER` | 0-based end coordinate of ORF in circular plasmid |
| `orf_strand` | `CHAR(1)` | `'+'` (forward) or `'-'` (reverse complement) |
| `orf_frame` | `INTEGER` | Reading frame: `0`, `1`, or `2` |
| `orf_score` | `REAL` | Alignment identity vs WT (0–1, WT-normalised) |
| `orf_coverage` | `REAL` | Alignment coverage vs WT (0–1, WT-normalised) |
| `orf_final` | `REAL` | Combined selection score (`score × length_similarity`) |
| `orf_protein_len` | `INTEGER` | Length of identified ORF protein (amino acids) |
| `orf_cds_dna` | `TEXT` | Coding DNA sequence of the identified ORF |
| `orf_protein_sequence` | `TEXT` | Translated protein sequence of the identified ORF |

### QC and metadata

| Column | Type | Description |
|---|---|---|
| `activity_score` | `REAL` | Reserved for functional activity data |
| `mutation_total` | `INTEGER` | Reserved for mutation count (populated in later pipeline steps) |
| `qc_passed` | `BOOLEAN DEFAULT TRUE` | Set to `FALSE` for records rejected by QC |
| `qc_reason` | `TEXT` | Reason if `qc_passed = FALSE` |
| `metadata` | `JSONB` | Extra columns from upload file not mapped to known fields |

---

## measurements

Yield measurements associated with a variant. Each variant gets one measurement row inserted at upload time.

| Column | Type | Description |
|---|---|---|
| `measurement_id` | `SERIAL PK` | Auto-incrementing ID |
| `variant_id` | `INTEGER FK → variants.variant_id` | Associated variant |
| `dna_yield` | `FLOAT` | DNA yield in femtograms (fg) |
| `protein_yield` | `FLOAT` | Protein yield in picograms (pg) |
| `is_control` | `BOOLEAN DEFAULT FALSE` | Whether this variant is a control |

---

## mutations

Reserved for mutation annotation (populated in future pipeline steps after ORF analysis identifies the coding sequence).

| Column | Type | Description |
|---|---|---|
| `mutation_id` | `SERIAL PK` | Auto-incrementing ID |
| `variant_id` | `INTEGER FK → variants.variant_id` | Associated variant |
| `position` | `INTEGER NOT NULL` | Amino acid position (1-based) |
| `wt_residue` | `CHAR(1)` | Wild-type amino acid |
| `mutant_residue` | `CHAR(1)` | Mutant amino acid |
| `mutation_type` | `VARCHAR(20)` | e.g. `'missense'`, `'synonymous'`, `'nonsense'` |
