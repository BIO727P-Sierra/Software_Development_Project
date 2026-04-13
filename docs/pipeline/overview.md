# Pipeline Overview

The Directed Evolution Portal implements a multi-step workflow that takes a researcher from a protein accession number through variant upload, automated ORF detection, mutation calling, activity scoring, and final visualisations.

---

## The full workflow

```mermaid
flowchart TD
    S1["🔍 Step 1 — UniProt Search<br/>Enter a UniProt accession ID<br/>Fetches WT protein sequence + annotated features"]
    S2["🧬 Step 2 — Plasmid Upload<br/>Upload the wild-type plasmid as a FASTA file<br/>Validates WT protein is encoded in it<br/>Stores the plasmid DNA sequence"]
    S3["📂 Step 3 — Experiment Data Upload<br/>Upload variant sequencing data as JSON or TSV<br/>Parses, validates, and inserts variant rows<br/>Associates DNA sequences, yields, generation info"]
    S4["🔬 Step 4 — ORF Analysis<br/>Scans each variant plasmid DNA for ORFs<br/>Scores each ORF against the WT protein<br/>Writes results back to the database"]
    S5["🧩 Step 5 — Mutation Calling<br/>Aligns each variant protein to WT<br/>Classifies differences as missense/nonsense/indel<br/>Populates the mutations table"]
    S6["📊 Step 6 — Activity Scoring<br/>Normalises DNA/protein yields against WT baseline<br/>Computes log₂ activity score per variant<br/>Feeds Top Performers table and visualisations"]

    S1 --> S2 --> S3 --> S4 --> S5 --> S6

    style S1 fill:#dbeafe,stroke:#2563eb,color:#000
    style S2 fill:#d1fae5,stroke:#059669,color:#000
    style S3 fill:#fce7f3,stroke:#db2777,color:#000
    style S4 fill:#ede9fe,stroke:#7c3aed,color:#000
    style S5 fill:#fef3c7,stroke:#d97706,color:#000
    style S6 fill:#fee2e2,stroke:#dc2626,color:#000
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
| 5 | Call mutations via WT protein alignment | [Mutation Calling](mutation-calling.md) |
| 6 | Compute activity scores and rank variants | [Activity Score](activity-score.md) |
| — | Explore results visually (box plot, fingerprint, landscape) | [Visualisations](visualisations.md) |
| — | Save, rename, report, or delete past experiments | [Experiment History](experiment-history.md) |
