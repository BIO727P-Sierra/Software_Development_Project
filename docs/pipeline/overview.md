# Pipeline Overview

The Directed Evolution Portal implements a four-step workflow that takes a researcher from a protein accession number all the way to scored ORF results for every variant in an experiment.

---

## The full workflow

```mermaid
flowchart TD
    S1["🔍 Step 1 — UniProt Search\nEnter a UniProt accession ID\nFetches WT protein sequence + annotated features"]
    S2["🧬 Step 2 — Plasmid Upload\nUpload the wild-type plasmid as a FASTA file\nValidates WT protein is encoded in it\nStores the plasmid DNA sequence"]
    S3["📂 Step 3 — Experiment Data Upload\nUpload variant sequencing data as JSON or TSV\nParses, validates, and inserts variant rows\nAssociates DNA sequences, yields, generation info"]
    S4["🔬 Step 4 — ORF Analysis\nScans each variant plasmid DNA for ORFs\nScores each ORF against the WT protein\nWrites results back to the database"]

    S1 --> S2 --> S3 --> S4

    style S1 fill:#dbeafe,stroke:#2563eb,color:#000
    style S2 fill:#d1fae5,stroke:#059669,color:#000
    style S3 fill:#fce7f3,stroke:#db2777,color:#000
    style S4 fill:#ede9fe,stroke:#7c3aed,color:#000
```

---

## Why this order matters

Each step depends on the one before it:

- **ORF analysis** requires knowing the WT protein (from UniProt) and the variant DNA sequences (from experiment upload)
- **Plasmid validation** requires the WT protein to confirm the plasmid is correct before any variants are uploaded
- **Experiment upload** is gated behind successful plasmid validation to prevent bad data entering the database

The app enforces this sequence via session state — attempting to skip steps redirects back to the appropriate stage.

---

## Data flow through the database

```mermaid
erDiagram
    users ||--o{ experiments : "owns"
    experiments ||--o{ variants : "contains"
    variants ||--o{ measurements : "has"
    variants ||--o{ mutations : "has"

    experiments {
        text wt_protein_sequence "set at Step 1"
        text wt_dna_sequence "set at Step 2"
    }
    variants {
        text assembled_dna_sequence "set at Step 3"
        text orf_protein_sequence "set at Step 4"
        real orf_score "set at Step 4"
        real orf_coverage "set at Step 4"
    }
```

---

## Step-by-step guides

| Step | What happens | Guide |
|---|---|---|
| 1 | Fetch WT protein + features from UniProt | [UniProt Search](uniprot.md) |
| 2 | Upload & validate the WT plasmid FASTA | [Plasmid Upload](plasmid-upload.md) |
| 3 | Upload variant sequencing data | [Experiment Upload](experiment-upload.md) |
| 4 | Run automated ORF analysis | [ORF Analysis](orf-analysis.md) |
