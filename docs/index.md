# Directed Evolution Portal

The **Directed Evolution Portal** is a web application for tracking and analysing protein engineering experiments. It guides researchers through a structured workflow — from retrieving a reference protein from UniProt, through plasmid validation and variant data upload, to automated ORF (open reading frame) identification and scoring.

---

## What it does

Directed evolution generates large libraries of protein variants by iteratively mutating a gene and selecting for improved function. This portal provides the informatics backbone for that process:

1. **Fetch a reference protein** from UniProt by accession ID
2. **Validate a plasmid** by confirming the WT protein is encoded in the uploaded sequence
3. **Upload variant data** (DNA sequences, yields, generation metadata) from sequencing runs
4. **Run ORF analysis** to automatically identify the coding sequence in each variant plasmid and score it against the wild-type reference

---

## Architecture overview

```mermaid
flowchart TB
 subgraph UI["UI Layer — Flask Templates"]
    direction LR
        ui1["Login / Register"]
        ui2a["Stage — UniProt Search"]
        ui2b["Stage — Plasmid Upload"]
        ui3["Upload Data"]
        ui4["Results & Visualisations"]
        ui5["My Experiments 🟡"]
  end
 subgraph FLASK["Flask Blueprints"]
    direction LR
        f1["auth.py ✅"]
        f2["uniprot.py ✅"]
        f3["FASTA_upload.py ✅"]
        f4["experiment_upload.py ✅"]
        f5["analysis.py ✅"]
        f6["visualisation.py ❌"]
  end
 subgraph BUILT["✅ Built"]
    direction LR
        s1["uniprotAPI.py"]
        s2["FASTA_parsing_logic.py"]
        s3["parse_data.py + qc.py"]
        s4["sequence_processor.py"]
  end
 subgraph TODO["❌ To Build"]
    direction LR
        s5["mutation_caller.py"]
        s6["activity_score.py"]
        s7["visualisation.py"]
  end
 subgraph SVC["Service / Logic Layer"]
    direction LR
        BUILT
        TODO
  end
 subgraph EXT["External"]
    direction LR
        ext1[("🌐 UniProt REST API")]
        ext2[("📁 File Storage")]
  end
 subgraph DB["Data Layer — PostgreSQL"]
    direction LR
        db1[("users")]
        db2[("experiments")]
        db3[("variants")]
        db4[("measurements")]
        db5[("mutations ❌")]
  end
 subgraph DOCS["📖 Documentation"]
    direction LR
        docs1["mkdocs"]
  end
    User(["👤 User"]) --> ui1 & ui2a & ui2b & ui3 & ui4
    ui1 --> f1
    ui2a --> f2
    ui2b --> f3
    ui3 --> f4
    ui4 --> f5 & f6
    f2 --> s1
    f3 --> s2
    f4 --> s3
    f5 --> s4
    f5 -.-> s5 & s6
    f6 -.-> s7
    s1 --> ext1 & db2
    s2 --> ext2
    s3 --> ext2 & db3 & db4
    f1 --> db1
    s4 --> db3
    s5 -.-> db5
    s6 -.-> db3
    s7 --> db3 & db4 & db5

    style BUILT fill:#d1fae5,stroke:#059669,color:#000
    style TODO fill:#fee2e2,stroke:#dc2626,color:#000
    style UI fill:#dbeafe,stroke:#2563eb,color:#000
    style FLASK fill:#fce7f3,stroke:#db2777,color:#000
    style SVC fill:#f0fdf4,stroke:#86efac,color:#000
    style EXT fill:#fef3c7,stroke:#d97706,color:#000
    style DB fill:#ede9fe,stroke:#7c3aed,color:#000
    style DOCS fill:#f5f5f5,stroke:#666666,color:#000
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Web framework | Flask 3.x |
| Authentication | Flask-Login |
| Database | PostgreSQL 16 (Docker) |
| ORM / DB driver | psycopg3 |
| Sequence analysis | Biopython |
| Deployment | Docker Compose + Gunicorn |

---

## Quick links

- [Getting Started](getting-started.md) — set up and run the app in minutes
- [Pipeline Overview](pipeline/overview.md) — understand the full experiment workflow
- [ORF Analysis](pipeline/orf-analysis.md) — deep dive into the sequence processing engine
- [Database Schema](reference/database-schema.md) — full table and column reference
